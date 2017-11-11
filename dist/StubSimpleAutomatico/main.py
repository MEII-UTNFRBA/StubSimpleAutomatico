# Imports de kivy

from kivy.uix.floatlayout import FloatLayout
from kivy.app import App
from kivy.properties import StringProperty
from kivy.uix.widget import Widget
from kivy.properties import NumericProperty, ReferenceListProperty
from kivy.vector import Vector
from kivy.clock import Clock
from kivy.config import Config

# Imports de otras

import visa
import serial
import math
import string
import time
from si_prefix import si_format

# Imports propios

from general_popups import ArduinoConnectPopup,VNAConnectPopup,NewStubPopup, ErrorPopup, StubDeletePopup, \
    MismaFrecPopup, RapidaPopup
from angcomp_functions import ang_sel_fnc,capa_sel_fnc,inductor_sel_fnc
from database import DataBase

########################################################################################################################
########################################################################################################################
########################################################################################################################

Config.set('graphics', 'resizable', False)                  # Para que no se deforme por resizear
Config.set('kivy', 'exit_on_escape', '0')                   # Para que no se cierre cuando se toca "Esc"
Config.set('input', 'mouse', 'mouse,multitouch_on_demand')  # Para que deje de poner el circulo naranja cuando tocas
                                                            #boton derecho con el mouse


class Main(FloatLayout):
    """
    Main del programa
    defs:
    *   __init__
    *   threadloop
    *   modesel_check
    *   stubsel_check
    *   arduino_test_connection
    *   vna_test_connection
    """

    vna_conectado = StringProperty()
    vna_showname = StringProperty()
    arduino_conectado = StringProperty()
    modulo_out = StringProperty()
    angulo_out = StringProperty()
    z_out = StringProperty()
#    frec_ol = ["First thing", "Second thing", "Third thing"]
    stub_sel = StringProperty()                         # Va a ser el stub que vaya a elegir

    mode_state = 0                                      # Modo en el que nos encontramos:
                                                        #   0: Calibracion precisa
                                                        #   1: Calibracion rapida
                                                        #   2: Lazo abierto preciso
                                                        #   3: Lazo abierto rapido

    basedatos = DataBase()                              # Correspondiete a la base de datos
    freq_precision_sel = 0                              # Frecuencia de precision elegida

    arduino_read = ""                                   # Para la lectura constante del arduino
    measure_vec = []

    def __init__(self):
        super(Main, self).__init__()
        self.vna_conectado = "Desconectado"             # Indica cual vna esta conectado (o dc si no hay)
        self.arduino_conectado = "Desconectado"         # Indica en cual port esta conectado el arduino (o dc si no hay)
        self.vna_showname = "Desconectado"              # El nombre que muestra (asi aparece solo fabr y modelo)
        Clock.schedule_interval(self.threadloop, 0.1)   # Me "interrumpe" cada 100 mseg
        self.rm = visa.ResourceManager()                # rm es un "tipo" visa
        self.start = 0                                  # Para los botones "Comenzar" y "Detener"
        self.modulo_out=str("MOD= ")                    # String que indica en pantalla lo dicho
        self.angulo_out=str("ANG= ")                    # String que indica en pantalla lo dicho
        self.z_out = str("COMP: ")                      # String que indica en pantalla lo dicho
        self.ang_sel = 0
        self.start = 0

        # Para la base de datos
        self.basedatos.conectar()                       # Me conecto
        self.basedatos.init()                           # Inicializo la base de datos

        self.stub_sel = "Seleccionar"                   # Es para saber que stub se eligio

        # Aca van a estar las funciones de loop que se ejecutaran en base al mode_state
        self.loop_switch = {0: self.mode0_loop,         # Una especie de switch/case.
                            1: self.mode1_loop,
                            2: self.mode2_loop,
                            3: self.mode3_loop
                            }

        self.freq_start_sel = ""                        # Frecuencia que voy a usar para cargar

        self.ROE = 0
        self.ANG_init = 0

        self.measure_real = 0
        self.measure_img = 0

        self.mode3_componente_elegido = 0

        # Flags para saber en que estado estoy del loop cuando comienza el programa
        self.mode0_state = 0
        self.mode1_state = 0
        self.mode2_state = 0
        self.mode3_state = 0

        self.serial_count = 0                           # Para esperar a que inicialice el serie
        self.mode0_count = 0                            # Para contar cuantas mediciones tomo en el modo 0
        self.mode1_count = 0                            # Para contar cuantas mediciones tomo en el modo 1

        self.long_onda = 0                              # Para conocer la longitud de onda en base a la frecuencia
        self.pasos_porgrado = 0                         # Calcula cuantos pasos tiene que dar para 1 grado en base a la
                                                        # frecuencia

        self.serie_arduino = serial.Serial()
        self.freq_usada = 0
        self.flag_delay = 0
        self.pasos_mover = 0
        self.inst = 0
########################################################################################################################
### Loop cada 100ms ####################################################################################################
########################################################################################################################

    def threadloop(self, dt):
        self.modesel_check()                            # En base al modo elegido, habilita o deshabilita widgets
        self.stubsel_check()
#        self.arduino_test_connection()                  # Chequea el estado del conexion del arduino
#        self.vna_test_connection()                      # Chequea el estado de conexion del vna

#        self.arduino_lectura()

        if self.start == 1:
            self.loop_switch[self.mode_state]()         # Elijo que ejecutar en base al estado de mode

########################################################################################################################
### Funciones dependientes del modo para cuando se presiona "Comenzar" #################################################
########################################################################################################################

### Mode0 ##############################################################################################################

    def mode0_loop(self):
        if self.vna_conectado == "Desconectado":
            txt = 'VNA desconectado'
            ErrorPopup(txt)
            self.start = 0                              # Para que no siga ejecutandose
            return

        if self.arduino_conectado == "Desconectado":
            txt = 'Arduino desconectado'
            ErrorPopup(txt)
            self.start = 0                              # Para que no siga ejecutandose
            return

        mode0_switch = { 0: self.mode0_switch0,
                         1: self.mode0_switch1,
                         2: self.mode0_switch2,
                         3: self.mode0_switch3,
                         }
        mode0_switch[self.mode0_state]()

    # Switchs del mode0_loop()
    def mode0_switch0(self):
#        #print "switch0"
        if self.serial_count >= 19:  # Espero a que se setee bien el serie
            self.serial_count = 0  # Para usarlo luego de la misma forma
            try:
                self.serie_arduino.write('I400U\n')  # Para asegurar la posicion en la que termine el empalme

                a = self.serie_arduino.read(20)  # Limpio lo que haya por leer al pedo
                self.serie_arduino.write('D20000U\n')  # Aca lo llevo al fin de carrera de la derecha
                #                time.sleep(0.)
                self.temp = 0  # Ni idea de donde salio
                self.mode0_state = 1  # Va al siguiente estado del
                #print("switch1")
            except (OSError, serial.SerialException):  # En caso de que haya algun problema escribiendo
                #print"Error switch0 mode1"
                self.arduino_conectado = "Desconectado"
                return
        else:
            self.serial_count += 1  # Seria como un timer de 0.1s cada vez que incrementa

    def mode0_switch1(self):
        #        if self.serial_count == 1:                          # Para esperar un ratito cuando escribo STATUS (0.1s)
        #        time.sleep(0.2)
        #print self.serie_arduino.inWaiting()  # Imprime si hay algo en la cola del serie
        if self.serie_arduino.inWaiting() > 0:
            self.arduino_read = self.serie_arduino.readline()  # Leo lo que haya en la cola
            #print(self.arduino_read)  # Imprime lo que lee

            if self.arduino_read == 'END_DER\r\n':  # Me fijo lo que recibi
                #self.serie_arduino.write('I10F\n')  # Muevo el stub para no tener en cuenta el error de la pieza
                ##print self.serie_arduino.readline()
                #self.serie_arduino.write('10\n')  # Muevo el stub para no tener en cuenta el error de la pieza
                ##print self.serie_arduino.readline()
                self.mode0_count = 0  # Para contar la cantidad de mediciones que voy a tomar
                self.serial_count = 0  # Por si necesito cotar de vuelta
                self.measure_vec = []  # Vectores para obtener los datos de real e img del vna
                self.pasos_porgrado = round(self.long_onda*10000/(2.11*36), 0)
                #print self.long_onda
                #print self.pasos_porgrado
                self.serie_arduino.read(20)
                self.serie_arduino.write("I10F\n")
                self.pasos_realizados = 10
                #print self.serie_arduino.readline()
                self.pasos_realizados = int(self.pasos_porgrado)
#                time.sleep(0.2)
                self.flag_delay = 0
                self.mode0_state = 2  # Para que pase al siguiente estado del switch
                self.serial_count = 0  # Por si necesito usarlo luego
                #print "switch2"

    def mode0_switch2(self):
        if self.serie_arduino.inWaiting() > 0:
            lectura_serial = self.serie_arduino.readline()
            #print lectura_serial
            lectura_serial = string.replace(lectura_serial, "I", "")
            lectura_serial = string.replace(lectura_serial, "F\n", "")
            if int(lectura_serial) < self.pasos_realizados:
                self.serie_arduino.write("STOP\n")
                #print "menos pasos"
                pasos_restante = int(self.pasos_porgrado) - int(lectura_serial)
                #print pasos_restante
                self.pasos_realizados = pasos_restante
                self.serie_arduino.read(20)
                self.serie_arduino.write("%s\n" % pasos_restante)
                lectura_serial = self.serie_arduino.readline()
                #print lectura_serial
            else:
                self.serial_count = 5
                self.flag_delay = 1

        if self.serial_count <= 0 and self.flag_delay == 1:
            dato = self.vna_lectura()
            count = 0
            while dato == -1:
                time.sleep(0.1)
                dato = self.vna_lectura()
                count += 1
                if count >= 10:
                    txt = "Error en comunicacion\ncon el VNA"
                    ErrorPopup(txt)
                    self.start = 0
                    return
            self.measure_vec.extend(dato)
            self.flag_delay = 0
            try:
                #self.serie_arduino.read(20)
                self.serie_arduino.write("%s\n" % int(self.pasos_porgrado))  # Me muevo los pasos necesarios
                self.pasos_realizados = self.pasos_porgrado
            except (OSError, serial.SerialException):
                #print("error")
                self.arduino_conectado = "Desconectado"
                return
            lectura_serial = self.serie_arduino.readline()
            #print lectura_serial
            self.mode0_count += 1
            if self.mode0_count <= 360:
                #print self.mode0_count
                self.mode0_state = 2
            else:
                self.mode0_state = 3
                #print "switch3"
        else:
            if self.flag_delay == 1:
                self.serial_count -= 1
            #print self.serial_count

    def mode0_switch3(self):
        #print self.measure_vec
        #print self.freq_input_check()
        self.basedatos.agregar_calibracion_adv(self.measure_vec, self.stub_sel, self.freq_input_check(), self.pasos_porgrado)
        self.start = 0
        self.serie_arduino.close()
        self.inst.close()

### Mode1 ##############################################################################################################

    def mode1_loop(self):
        if self.vna_conectado == "Desconectado":
            txt = 'VNA desconectado'
            ErrorPopup(txt)
            self.start = 0                              # Para que no siga ejecutandose
            self.serie_arduino.close()
            self.inst.close()
            return

        if self.arduino_conectado == "Desconectado":
            txt = 'Arduino desconectado'
            ErrorPopup(txt)
            self.start = 0                              # Para que no siga ejecutandose
            self.serie_arduino.close()
            self.inst.close()
            return

        #if self.start == 0:
        #    return

        mode1_switch = { 0: self.mode1_switch0,
                         1: self.mode1_switch1,
                         2: self.mode1_switch2,
                         3: self.mode1_switch3,
                         }
        mode1_switch[self.mode1_state]()

    # Switchs del mode1_loop()
    def mode1_switch0(self):
        if self.serial_count >= 19:                         # Espero a que se setee bien el serie
            self.serial_count = 0                           # Para usarlo luego de la misma forma
            try:
                self.serie_arduino.write('I400U\n')         # Para asegurar la posicion en la que termine el empalme

                a = self.serie_arduino.read(999)            # Limpio lo que haya por leer al pedo
                self.serie_arduino.write('D20000U\n')       # Aca lo llevo al fin de carrera de la derecha
#                time.sleep(0.)
                self.temp = 0                               # Ni idea de donde salio
                self.mode1_state = 1                        # Va al siguiente estado del switch
            except (OSError, serial.SerialException):       # En caso de que haya algun problema escribiendo
                #print"Error switch0 mode1"
                self.arduino_conectado = "Desconectado"
                return
        else:
            self.serial_count += 1                          # Seria como un timer de 0.1s cada vez que incrementa

    def mode1_switch1(self):
        #print("entro")
#        if self.serial_count == 1:                          # Para esperar un ratito cuando escribo STATUS (0.1s)
#        time.sleep(0.2)
        self.serial_count = 0                           # Por si necesito usarlo luego
        #print self.serie_arduino.inWaiting()            # Imprime si hay algo en la cola del serie
        if self.serie_arduino.inWaiting() > 0:
            self.arduino_read = self.serie_arduino.readline()   # Leo lo que haya en la cola
            #print(self.arduino_read)                        # Imprime lo que lee

        if self.arduino_read == 'END_DER\r\n':          # Me fijo lo que recibi
            self.serie_arduino.read(20)
            self.serie_arduino.write('I10F\n')          # Muevo el stub para no tener en cuenta el error de la pieza
            self.serie_arduino.readline()
            #print("mongo")                              # "mongo"
            self.mode1_count = 0                        # Para contar la cantidad de mediciones que voy a tomar
            self.serial_count = 0                       # Por si necesito cotar de vuelta
            self.measure_vec = []                       # Vectores para obtener los datos de real e img del vna
            self.mode1_state = 2                        # Para que pase al siguiente estado del switch
            self.complete_m1_s1 = 0
            self.m1_s1_state = 0
            self.pasos_realizados = 10
            self.pasos_mover = 100
#        else:
#            try:
#                time.sleep(10)
#                a = self.serie_arduino.read(999)                # Limpio lo que haya por leer al pedo
#                self.serie_arduino.write("STATUS\n")            # Le pregunto en donde anda el arduino (datos)
#                self.serial_count = 1
#            except (OSError, serial.SerialException):
#                #print("error de mode1 switch 1 de END_DER")
#                self.arduino_conectado = "Desconectado"
#                return

    def mode1_switch2(self):
        m1_s1_switch = {0: self.m1_s1_leer,
                        1: self.m1_s1_850,
                        2: self.m1_s1_sweep_1_8,
                        3: self.m1_s1_mover,
                        4: self.m1_s1_delay,
                        }
        m1_s1_switch[self.m1_s1_state]()
        if self.complete_m1_s1 == 1:
            self.mode1_state = 3

    def m1_s1_delay(self):
        self.count_delay -= 1
        #print self.count_delay
        if self.count_delay == 0:
            self.flag_delay = 1
            self.m1_s1_state = self.switch_anterior

    def m1_s1_leer(self):
        if self.serie_arduino.inWaiting() > 0:
            lectura_serial = self.serie_arduino.readline()  # Leo lo que haya en la cola
            #print "leo cuando termina los pasos y cuanto hizo"
            #print lectura_serial
            lectura_serial = string.replace(lectura_serial, "I", "")
            lectura_serial = string.replace(lectura_serial, "F\n", "")
            if int(lectura_serial) < self.pasos_realizados:
                self.serie_arduino.write("STOP\n")
                #print "menos pasos"
                pasos_restante = int(self.pasos_mover) - int(lectura_serial)
                #print pasos_restante
                self.pasos_realizados = pasos_restante
                self.serie_arduino.read(20)
                self.serie_arduino.write("I%sF\n" % pasos_restante)
                lectura_serial = self.serie_arduino.readline()
                #print lectura_serial
            else:
                self.m1_s1_state = 1
                self.flag_delay = 0

    def m1_s1_850(self):
        if self.flag_delay == 0:
            #print "entro 850"
            if self.vna_setfreq("850E6", "850E6", "2") == -1:
                self.vna_conectado = "Desconectado"
                self.vna_showname = "Desconectado"
                return
            self.switch_anterior = self.m1_s1_state
            self.m1_s1_state = 4
            self.count_delay = 5
        else:
            measure_850 = []

            # No uso vna_lectura() porque no me sirve para medir como esta configurado para este modo
            # Leo los datos del vna para 850MHz
            try:
                #            inst = self.rm.open_resource(self.vna_conectado)
                measure_850_aux = self.inst.query_ascii_values("CALC:SEL:DATA:SDAT?")  # Para leer real imag en 850
                measure_850_r = measure_850_aux[0]  # +measure_850_aux[2])/2
                measure_850_i = measure_850_aux[1]  # +measure_850_aux[3])/2

                ROE = math.sqrt(pow(measure_850_i, 2) + pow(measure_850_r, 2))
                ang_aux = math.degrees(math.atan(measure_850_i / measure_850_r))  # Calculo el angulo
                if measure_850_r > 0 and measure_850_i > 0:  # Correccion del angulo para tenerlo de
                    # 0 a 360 grados
                    ang = ang_aux
                elif measure_850_r < 0 < measure_850_i:
                    ang = 180 + ang_aux
                elif measure_850_r < 0 and measure_850_i < 0:
                    ang = 180 + ang_aux
                else:
                    ang = 360 + ang_aux

                measure_850.append(ROE)
                measure_850.append(ang)

                self.angulo_out = str("ANG= %s" % round(ang, 3))  # Lo que va a imprimir con el angulo
                self.modulo_out = str("MOD= %s" % round(ROE, 5))  # Lo que va a imprimir con el modulo

                s_complex = complex(measure_850_r, measure_850_i)  # Paso la medicion a compleja
                z_aux = (1 + s_complex) / (1 - s_complex) * 50  # Calculo la impedancia
                if measure_850_i < 0:  # Imprime la L o C en base a la freq
                    z_posta = -1 / (z_aux.imag * 2 * math.pi * pow(10, 9))
                    self.z_out = str("COMP: C = %sF" % si_format(z_posta, precision=2))
                else:
                    z_posta = z_aux.imag / (2 * math.pi * pow(10, 9))
                    self.z_out = str("COMP: L = %sH" % si_format(z_posta, precision=2))

                self.move_point(round(measure_850_r * 122, 0),
                                round(measure_850_i * 122, 0))  # Mueve el punto
                #            inst.close()
            except visa.VisaIOError:  # Si no se puede hacer, es que se dc o algo
                # self.start = 0
                # inst.close()
                #print("Se rompe el vna")
                self.vna_showname = "Desconectado"
                self.vna_conectado = "Desconectado"
                return
            self.measure_vec.extend(measure_850)
            self.m1_s1_state = 2
            self.flag_delay = 0

    def m1_s1_sweep_1_8(self):
        if self.flag_delay == 0:
            if self.vna_setfreq("1E9", "8E9", "8") == -1:
                self.vna_conectado = "Desconectado"
                self.vna_showname = "Desconectado"
                return
            self.switch_anterior = self.m1_s1_state
            self.m1_s1_state = 4
            self.count_delay = 5
        else:
            measure = []
            # No uso vna_lectura() porque no me sirve para medir como esta configurado para este modo
            # Leo los datos del vna para 1 a 8GHz
            try:
                #            inst = self.rm.open_resource(self.vna_conectado)
                measure_aux = self.inst.query_ascii_values("CALC:SEL:DATA:SDAT?")  # Para leer real imag
                for i in range(0, 16, 2):
                    ROE = math.sqrt(pow(measure_aux[i], 2) + pow(measure_aux[i + 1], 2))
                    ang_aux = math.degrees(math.atan(measure_aux[i + 1] / measure_aux[i]))  # Calculo el angulo
                    if measure_aux[i] > 0 and measure_aux[i + 1] > 0:  # Correccion del angulo para tenerlo de
                        # 0 a 360 grados
                        ang = ang_aux
                    elif measure_aux[i] < 0 < measure_aux[i + 1]:
                        ang = 180 + ang_aux
                    elif measure_aux[i] < 0 and measure_aux[i + 1] < 0:
                        ang = 180 + ang_aux
                    else:
                        ang = 360 + ang_aux
                    measure.append(ROE)
                    measure.append(ang)
                    #            inst.close()
            except visa.VisaIOError:  # Si no se puede hacer, es que se dc o algo
                # inst.close()
                # self.start = 0
                #print("Se rompe el vna")
                self.vna_showname = "Desconectado"
                self.vna_conectado = "Desconectado"
                return

            # Guardo los datos real e imaginario en los vectores correspondientes
            self.measure_vec.extend(measure)
            #print(self.measure_vec)
            self.m1_s1_state = 3
            self.flag_delay = 0

    def m1_s1_mover(self):
        # Voy moviendo el stub
        try:
            self.serie_arduino.write("I%sF\n" % self.pasos_mover)
        except (OSError, serial.SerialException):
            #print("error")
            self.arduino_conectado = "Desconectado"
            return

        self.mode1_count += 1
        if self.mode1_count >= 21:
            self.mode1_state = 3
        self.m1_s1_state = 0
        self.flag_delay = 0

    def mode1_switch3(self):
        # Aca cargaria la base de datos
        measure_delta_vec = [i for i in range(len(self.measure_vec)-18)]
        measure_delta_prom_vec = [0]*18
        calibracion = []
        for i in range(18, (len(self.measure_vec))):
            aux = abs(self.measure_vec[i] - self.measure_vec[i-18])
            if aux > 30:
                measure_delta_vec[i-18] = 360 - aux
            else:
                measure_delta_vec[i-18] = aux

        for j in range(0, 18):
            for i in range(0, len(measure_delta_vec), 18):
                measure_delta_prom_vec[j] = measure_delta_prom_vec[j] + measure_delta_vec[i+j]
            measure_delta_prom_vec[j] = measure_delta_prom_vec[j]/len(measure_delta_vec)*18
        calibracion.extend(measure_delta_prom_vec)
        for i in range(0, 18):
            calibracion.append(self.measure_vec[i])
        self.basedatos.agregar_calibracion_rapida(calibracion, self.stub_sel)
        self.start = 0
        self.serie_arduino.close()
        self.inst.close()

### Mode2 ##############################################################################################################

    def mode2_loop(self):
        if self.arduino_conectado == "Desconectado":
            txt = 'Arduino desconectado'
            ErrorPopup(txt)
            self.start = 0                              # Para que no siga ejecutandose


        mode2_switch = {0: self.mode2_switch0,
                        1: self.mode2_switch1,
                        2: self.mode2_switch2,
                        3: self.mode2_switch3,
                        }
        mode2_switch[self.mode2_state]()
        #if self.start == 0:
        #    return

    def mode2_switch0(self):
        #print "switch0"
        if self.serial_count >= 19:  # Espero a que se setee bien el serie
            self.serial_count = 0  # Para usarlo luego de la misma forma
            try:
                self.serie_arduino.write('I400U\n')  # Para asegurar la posicion en la que termine el empalme

                #a = self.serie_arduino.read(20)  # Limpio lo que haya por leer al pedo
                self.serie_arduino.write('D20000U\n')  # Aca lo llevo al fin de carrera de la derecha
                a = self.serie_arduino.read(20)  # Limpio lo que haya por leer al pedo
                #                time.sleep(0.)
                self.temp = 0  # Ni idea de donde salio
                self.mode2_state = 1  # Va al siguiente estado del
                #print("switch1")
            except (OSError, serial.SerialException):  # En caso de que haya algun problema escribiendo
                #print"Error switch3 mode1"
                self.arduino_conectado = "Desconectado"
                return
        else:
            self.serial_count += 1  # Seria como un timer de 0.1s cada vez que incrementa

    def mode2_switch1(self):
        #        if self.serial_count == 1:                          # Para esperar un ratito cuando escribo STATUS (0.1s)
        #        time.sleep(0.2)
        #print self.serie_arduino.inWaiting()  # Imprime si hay algo en la cola del serie
        if self.serie_arduino.inWaiting() > 0:
            self.arduino_read = self.serie_arduino.readline()  # Leo lo que haya en la cola
            #print(self.arduino_read)  # Imprime lo que lee

            if self.arduino_read == 'END_DER\r\n':  # Me fijo lo que recibi
                self.serie_arduino.write('I10F\n')  # Muevo el stub para no tener en cuenta el error de la pieza
                #print self.serie_arduino.readline()
                # self.serie_arduino.write('10\n')  # Muevo el stub para no tener en cuenta el error de la pieza
                # #print self.serie_arduino.readline()
                #                self.mode0_count = 0  # Para contar la cantidad de mediciones que voy a tomar
                #                self.serial_count = 0  # Por si necesito cotar de vuelta
                #                self.measure_vec = []  # Vectores para obtener los datos de real e img del vna
                #                self.pasos_porgrado = round(self.long_onda * 10000 / (2.11 * 36), 0)
                #                #print self.long_onda
                #                #print self.pasos_porgrado
                self.serie_arduino.read(20)
                ang_aux = math.degrees(math.atan(self.measure_img_inicial / self.measure_real_inicial))
                if self.measure_real_inicial > 0 and self.measure_img_inicial > 0:  # Correccion del angulo para tenerlo de
                    # 0 a 360 grados
                    ang_aux = ang_aux
                elif self.measure_real_inicial < 0 < self.measure_img_inicial:
                    ang_aux = 180 + ang_aux
                elif self.measure_real_inicial < 0 and self.measure_img_inicial < 0:
                    ang_aux = 180 + ang_aux
                else:
                    ang_aux = 360 + ang_aux

                self.angulo_out = str("ANG= %s" % round(ang_aux, 3))  # Lo que va a imprimir con el angulo
                self.modulo_out = str("MOD= %s" % round(
                    math.sqrt(self.measure_real_inicial * self.measure_real_inicial + self.measure_img_inicial * self.measure_img_inicial),
                    5))  # Lo que va a imprimir con el modulo

                s_complex = complex(self.measure_real_inicial, self.measure_img_inicial)  # Paso la medicion a compleja
                z_aux = (1 + s_complex) / (1 - s_complex) * 50  # Calculo la impedancia
                if self.measure_img_inicial < 0:  # Imprime la L o C en base a la freq
                    z_posta = -1 / (z_aux.imag * 2 * math.pi * pow(10, 9) * self.freq_usada)
                    self.z_out = str("COMP: C = %sF" % si_format(z_posta, precision=2))
                else:
                    z_posta = z_aux.imag / (2 * math.pi * pow(10, 9) * self.freq_usada)
                    self.z_out = str("COMP: L = %sH" % si_format(z_posta, precision=2))

                self.move_point(round(self.measure_real_inicial * 122, 0), round(self.measure_img_inicial * 122, 0))  # Mueve el punto
                #                self.serie_arduino.write("I%sF\n" % int(self.pasos_porgrado))
                #                #print self.serie_arduino.readline()
                #                self.pasos_realizados = int(self.pasos_porgrado)
                #                time.sleep(0.2)
                self.mode2_state = 2  # Para que pase al siguiente estado del switch
                self.serial_count = 0  # Por si necesito usarlo luego
                #print "switch2"

    def mode2_switch2(self):
        self.serie_arduino.read(20)
        self.serie_arduino.write("I%sU\n" % int(self.pasos_mover))
        #self.serie_arduino.write("I200U\n")
        #print self.serie_arduino.readline()
        self.pasos_realizados = self.pasos_mover
        self.mode2_state = 3

    def mode2_switch3(self):
        if self.serie_arduino.inWaiting() > 0:
            self.arduino_read = self.serie_arduino.readline()  # Leo lo que haya en la cola
            #print self.arduino_read
            if int(self.arduino_read) < self.pasos_realizados:
                self.serie_arduino.write("STOP\n")
                #print "menos pasos"
                pasos_restante = int(self.pasos_mover) - int(self.arduino_read)
                #print pasos_restante
                self.pasos_realizados = pasos_restante
                self.serie_arduino.read(20)
                self.serie_arduino.write("%s\n" % pasos_restante)
                lectura_serial = self.serie_arduino.readline()
                #print lectura_serial
            else:
                self.start = 0
                self.serie_arduino.close()
#                self.inst.close()

                ang_aux = math.degrees(math.atan(self.measure_img / self.measure_real))
                if self.measure_real > 0 and self.measure_img > 0:  # Correccion del angulo para tenerlo de
                    # 0 a 360 grados
                    ang_aux = ang_aux
                elif self.measure_real < 0 < self.measure_img:
                    ang_aux = 180 + ang_aux
                elif self.measure_real < 0 and self.measure_img < 0:
                    ang_aux = 180 + ang_aux
                else:
                    ang_aux = 360 + ang_aux

                self.angulo_out = str("ANG= %s" % round(ang_aux, 3))  # Lo que va a imprimir con el angulo
                self.modulo_out = str("MOD= %s" % round(math.sqrt(self.measure_real*self.measure_real + self.measure_img*self.measure_img), 5))  # Lo que va a imprimir con el modulo

                s_complex = complex(self.measure_real, self.measure_img)  # Paso la medicion a compleja
                z_aux = (1 + s_complex) / (1 - s_complex) * 50  # Calculo la impedancia
                if self.measure_img < 0:  # Imprime la L o C en base a la freq
                    z_posta = -1 / (z_aux.imag * 2 * math.pi * pow(10, 9) * self.freq_usada)
                    self.z_out = str("COMP: C = %sF" % si_format(z_posta, precision=2))
                else:
                    z_posta = z_aux.imag / (2 * math.pi * pow(10, 9) * self.freq_usada)
                    self.z_out = str("COMP: L = %sH" % si_format(z_posta, precision=2))

                self.move_point(round(self.measure_real * 122, 0), round(self.measure_img * 122, 0))  # Mueve el punto

    ### Mode3 ##############################################################################################################

    def mode3_loop(self):
        if self.arduino_conectado == "Desconectado":
            txt = 'Arduino desconectado'
            ErrorPopup(txt)
            self.start = 0                              # Para que no siga ejecutandose

            med_basedatos = []

        mode3_switch = { 0: self.mode3_switch0,
                         1: self.mode3_switch1,
                         2: self.mode3_switch2,
                         3: self.mode3_switch3,
                         }
        mode3_switch[self.mode3_state]()

    # Switchs del mode3_loop()
    def mode3_switch0(self):
        #print "switch0"
        if self.serial_count >= 19:  # Espero a que se setee bien el serie
            self.serial_count = 0  # Para usarlo luego de la misma forma
            try:
                self.serie_arduino.write('I400U\n')  # Para asegurar la posicion en la que termine el empalme

                a = self.serie_arduino.read(999)  # Limpio lo que haya por leer al pedo
                self.serie_arduino.write('D20000U\n')  # Aca lo llevo al fin de carrera de la derecha
                #                time.sleep(0.)
                self.temp = 0  # Ni idea de donde salio
                self.mode3_state = 1  # Va al siguiente estado del
                #print("switch1")
            except (OSError, serial.SerialException):  # En caso de que haya algun problema escribiendo
                #print"Error switch3 mode1"
                self.arduino_conectado = "Desconectado"
                return
        else:
            self.serial_count += 1  # Seria como un timer de 0.1s cada vez que incrementa

    def mode3_switch1(self):
        #        if self.serial_count == 1:                          # Para esperar un ratito cuando escribo STATUS (0.1s)
        #        time.sleep(0.2)
        #print self.serie_arduino.inWaiting()  # Imprime si hay algo en la cola del serie
        if self.serie_arduino.inWaiting() > 0:
            self.arduino_read = self.serie_arduino.readline()  # Leo lo que haya en la cola
            #print(self.arduino_read)  # Imprime lo que lee

            if self.arduino_read == 'END_DER\r\n':  # Me fijo lo que recibi
                self.serie_arduino.write('I10F\n')  # Muevo el stub para no tener en cuenta el error de la pieza
                #print self.serie_arduino.readline()
                # self.serie_arduino.write('10\n')  # Muevo el stub para no tener en cuenta el error de la pieza
                # #print self.serie_arduino.readline()
#                self.mode0_count = 0  # Para contar la cantidad de mediciones que voy a tomar
#                self.serial_count = 0  # Por si necesito cotar de vuelta
#                self.measure_vec = []  # Vectores para obtener los datos de real e img del vna
#                self.pasos_porgrado = round(self.long_onda * 10000 / (2.11 * 36), 0)
#                #print self.long_onda
#                #print self.pasos_porgrado
                self.serie_arduino.read(20)

                ang_aux = math.degrees(math.atan(self.measure_img_inicial / self.measure_real_inicial))
                if self.measure_real_inicial > 0 and self.measure_img_inicial > 0:  # Correccion del angulo para tenerlo de
                    # 0 a 360 grados
                    ang_aux = ang_aux
                elif self.measure_real_inicial < 0 < self.measure_img_inicial:
                    ang_aux = 180 + ang_aux
                elif self.measure_real_inicial < 0 and self.measure_img_inicial < 0:
                    ang_aux = 180 + ang_aux
                else:
                    ang_aux = 360 + ang_aux

                self.angulo_out = str("ANG= %s" % round(ang_aux, 3))  # Lo que va a imprimir con el angulo
                self.modulo_out = str("MOD= %s" % round(
                    math.sqrt(
                        self.measure_real_inicial * self.measure_real_inicial + self.measure_img_inicial * self.measure_img_inicial),
                    5))  # Lo que va a imprimir con el modulo

                s_complex = complex(self.measure_real_inicial, self.measure_img_inicial)  # Paso la medicion a compleja
                z_aux = (1 + s_complex) / (1 - s_complex) * 50  # Calculo la impedancia
                if self.measure_img_inicial < 0:  # Imprime la L o C en base a la freq
                    z_posta = -1 / (z_aux.imag * 2 * math.pi * pow(10, 9))
                    self.z_out = str("COMP: C = %sF" % si_format(z_posta, precision=2))
                else:
                    z_posta = z_aux.imag / (2 * math.pi * pow(10, 9))
                    self.z_out = str("COMP: L = %sH" % si_format(z_posta, precision=2))

                self.move_point(round(self.measure_real_inicial * 122, 0), round(self.measure_img_inicial * 122, 0))  # Mueve el punto
#                self.serie_arduino.write("I%sF\n" % int(self.pasos_porgrado))
#                #print self.serie_arduino.readline()
#                self.pasos_realizados = int(self.pasos_porgrado)
#                time.sleep(0.2)
                self.mode3_state = 2  # Para que pase al siguiente estado del switch
                self.serial_count = 0  # Por si necesito usarlo luego
                #print "switch2"

    def mode3_switch2(self):
        ang_mover = self.ang_sel - self.ANG_init
        if ang_mover > 0:
            ang_mover = 360 - ang_mover
        elif ang_mover == 0:
            ang_mover = 0
        else:
            ang_mover = abs(ang_mover)
        #print "ang_mover"
        #print ang_mover
        #print "ang_init"
        #print self.ANG_init

        pasos_mover = ang_mover*100/self.deltaANG
#        pasos_mover = (0.3*200000/4.22)*(ang_mover/360)
        #print "pasos a mover:"
        #print pasos_mover

        self.serie_arduino.write("I%sU\n" % int(pasos_mover))
        #print self.serie_arduino.readline()
        self.mode3_state = 3

    def mode3_switch3(self):
        if self.serie_arduino.inWaiting() > 0:
            self.arduino_read = self.serie_arduino.readline()  # Leo lo que haya en la cola
            #print self.arduino_read
            self.start = 0
            self.serie_arduino.close()
#            self.inst.close()

            ang_aux = math.degrees(math.atan(self.measure_img / self.measure_real))
            if self.measure_real > 0 and self.measure_img > 0:  # Correccion del angulo para tenerlo de
                # 0 a 360 grados
                ang_aux = ang_aux
            elif self.measure_real < 0 < self.measure_img:
                ang_aux = 180 + ang_aux
            elif self.measure_real < 0 and self.measure_img < 0:
                ang_aux = 180 + ang_aux
            else:
                ang_aux = 360 + ang_aux

            self.angulo_out = str("ANG= %s" % round(ang_aux, 3))  # Lo que va a imprimir con el angulo
            self.modulo_out = str(
                "MOD= %s" % round(math.sqrt(self.measure_real * self.measure_real + self.measure_img * self.measure_img),
                                  5))  # Lo que va a imprimir con el modulo

            s_complex = complex(self.measure_real, self.measure_img)  # Paso la medicion a compleja
            z_aux = (1 + s_complex) / (1 - s_complex) * 50  # Calculo la impedancia
            if self.measure_img < 0:  # Imprime la L o C en base a la freq
                z_posta = -1 / (z_aux.imag * 2 * math.pi * pow(10, 9))
                self.z_out = str("COMP: C = %sF" % si_format(z_posta, precision=2))
            else:
                z_posta = z_aux.imag / (2 * math.pi * pow(10, 9))
                self.z_out = str("COMP: L = %sH" % si_format(z_posta, precision=2))

            self.move_point(round(self.measure_real * 122, 0), round(self.measure_img * 122, 0))  # Mueve el punto


########################################################################################################################
### Chequea el modo elegido y, en base a eso, habilita o deshabilita widgets ###########################################
########################################################################################################################

    def modesel_check(self):
        if self.start == 0:                                     # Para que cuando salga del start vuelva esto
            # Habilito el boton comenzar
            self.ids.start.disabled = False

            # Habilito el conectar con arduino y la seleccion del stub
            self.ids.stub_text.disabled = False
            self.ids.stop.disabled = True
            self.ids.stub_sel_id.disabled = False
            self.ids.stub_borrar_id.disabled = False
            self.ids.arduino_connect.disabled = False
            self.ids.port_text.disabled = False

            self.ids.operation_text.disabled = False
            self.ids.calibracionprecision_checkbox.disabled = False
            self.ids.calibracionprecision_text.disabled = False
            self.ids.calibracionrapida_checkbox.disabled = False
            self.ids.calibracionrapida_text.disabled = False
            self.ids.openloopprecision_checkbox.disabled = False
            self.ids.openloopprecision_text.disabled = False
            self.ids.openlooprapido_checkbox.disabled = False
            self.ids.openlooprapido_text.disabled = False

            if self.ids.calibracionprecision_checkbox.active:
                self.mode_state = 0                             # Para indicar que estoy en este modo

                # Deshabilito el Comenzar y Detener
                self.ids.start.disabled = False

                # Activo lo que tenga que ver con el vna
                self.ids.vna_connect.disabled = False
                self.ids.vna_text.disabled = False
                self.ids.calibracion_puerto_text.disabled = False
                self.ids.calibracion_seteo_puerto1.disabled = False
                self.ids.calibracion_seteo_puerto1_text.disabled = False
                self.ids.calibracion_seteo_puerto2.disabled = False
                self.ids.calibracion_seteo_puerto2_text.disabled = False

                #Dejo solo la seleccion de frecuencia como input
                self.ids.freq_text.disabled = False
                self.ids.freq_input.disabled = False
                self.ids.freq_text_unidad.disabled = False
                self.ids.frec_precision.disabled = True

                # Deshabilito el seteo de componente o angulo
                self.ids.angcomp_text.disabled = True
                self.ids.angcomp_input.disabled = True
                self.ids.angcomp_seteo_angulo.disabled = True
                self.ids.angcomp_seteo_angulo_text.disabled = True
                self.ids.angcomp_seteo_capacitor.disabled = True
                self.ids.angcomp_seteo_c_text.disabled = True
                self.ids.angcomp_seteo_inductor.disabled = True
                self.ids.angcomp_seteo_l_text.disabled = True

            elif self.ids.calibracionrapida_checkbox.active:
                self.mode_state = 1                             # Para indicar que estoy en este modo

                # Deshabilito el Comenzar y Detener
                self.ids.start.disabled = False

                # Activo lo que tenga que ver con el vna
                self.ids.vna_connect.disabled = False
                self.ids.vna_text.disabled = False
                self.ids.calibracion_puerto_text.disabled = False
                self.ids.calibracion_seteo_puerto1.disabled = False
                self.ids.calibracion_seteo_puerto1_text.disabled = False
                self.ids.calibracion_seteo_puerto2.disabled = False
                self.ids.calibracion_seteo_puerto2_text.disabled = False

                #Saco lo que tenga que ver con seleccion de frecuencia
                self.ids.freq_text.disabled = True
                self.ids.freq_input.disabled = True
                self.ids.freq_text_unidad.disabled =True
                self.ids.frec_precision.disabled = True

                # Deshabilito el seteo de componente o angulo
                self.ids.angcomp_text.disabled = True
                self.ids.angcomp_input.disabled = True
                self.ids.angcomp_seteo_angulo.disabled = True
                self.ids.angcomp_seteo_angulo_text.disabled = True
                self.ids.angcomp_seteo_capacitor.disabled = True
                self.ids.angcomp_seteo_c_text.disabled = True
                self.ids.angcomp_seteo_inductor.disabled = True
                self.ids.angcomp_seteo_l_text.disabled = True

            elif self.ids.openloopprecision_checkbox.active:
                self.mode_state = 2                             # Para indicar que estoy en este modo

                # Deshabilito el Comenzar y Detener
                self.ids.start.disabled = False

                # Desactivo lo que tenga que ver con el vna
                self.ids.vna_connect.disabled = True
                self.ids.vna_text.disabled = True
                self.ids.calibracion_puerto_text.disabled = True
                self.ids.calibracion_seteo_puerto1.disabled = True
                self.ids.calibracion_seteo_puerto1_text.disabled = True
                self.ids.calibracion_seteo_puerto2.disabled = True
                self.ids.calibracion_seteo_puerto2_text.disabled = True

                # Dejo solo la seleccion de frecuencia como seleccion especifica
                self.ids.freq_text.disabled = False
                self.ids.freq_input.disabled = True
                self.ids.freq_text_unidad.disabled = True
                self.ids.frec_precision.disabled = False

                # Habilito el seteo de componente o angulo
                self.ids.angcomp_text.disabled = False
                self.ids.angcomp_input.disabled = False
                self.ids.angcomp_seteo_angulo.disabled = False
                self.ids.angcomp_seteo_angulo_text.disabled = False
                self.ids.angcomp_seteo_capacitor.disabled = False
                self.ids.angcomp_seteo_c_text.disabled = False
                self.ids.angcomp_seteo_inductor.disabled = False
                self.ids.angcomp_seteo_l_text.disabled = False

            else:                                               # Seria que este activo el ultimo
                self.mode_state = 3                             # Para indicar que estoy en este modo

                # Deshabilito el Comenzar y Detener
                self.ids.start.disabled = False

                # Desactivo lo que tenga que ver con el vna
                self.ids.vna_connect.disabled = True
                self.ids.vna_text.disabled = True
                self.ids.calibracion_puerto_text.disabled = True
                self.ids.calibracion_seteo_puerto1.disabled = True
                self.ids.calibracion_seteo_puerto1_text.disabled = True
                self.ids.calibracion_seteo_puerto2.disabled = True
                self.ids.calibracion_seteo_puerto2_text.disabled = True

                # Dejo solo la seleccion de frecuencia como input
                self.ids.freq_text.disabled = False
                self.ids.freq_input.disabled = False
                self.ids.freq_text_unidad.disabled = False
                self.ids.frec_precision.disabled = True

                # Habilito el seteo de componente o angulo
                self.ids.angcomp_text.disabled = False
                self.ids.angcomp_input.disabled = False
                self.ids.angcomp_seteo_angulo.disabled = False
                self.ids.angcomp_seteo_angulo_text.disabled = False
                self.ids.angcomp_seteo_capacitor.disabled = False
                self.ids.angcomp_seteo_c_text.disabled = False
                self.ids.angcomp_seteo_inductor.disabled = False
                self.ids.angcomp_seteo_l_text.disabled = False

        else:                                                           # De lo mas horrible que se haya visto
            # Deshabilito el boton comenzar y habilito el de parar
            self.ids.start.disabled = True
            self.ids.stop.disabled = False
            # Deshabilito el conectar con arduino y la seleccion del stub
            self.ids.stub_text.disabled = True
            self.ids.stub_sel_id.disabled = True
            self.ids.stub_borrar_id.disabled = True
            self.ids.arduino_connect.disabled = True
            self.ids.port_text.disabled = True

            # Deshabilito los modos
            self.ids.operation_text.disabled = True
            self.ids.calibracionprecision_checkbox.disabled = True
            self.ids.calibracionprecision_text.disabled = True
            self.ids.calibracionrapida_checkbox.disabled = True
            self.ids.calibracionrapida_text.disabled = True
            self.ids.openloopprecision_checkbox.disabled = True
            self.ids.openloopprecision_text.disabled = True
            self.ids.openlooprapido_checkbox.disabled = True
            self.ids.openlooprapido_text.disabled = True

            # Desactivo lo que tenga que ver con el vna
            self.ids.vna_connect.disabled = True
            self.ids.vna_text.disabled = True
            self.ids.calibracion_puerto_text.disabled = True
            self.ids.calibracion_seteo_puerto1.disabled = True
            self.ids.calibracion_seteo_puerto1_text.disabled = True
            self.ids.calibracion_seteo_puerto2.disabled = True
            self.ids.calibracion_seteo_puerto2_text.disabled = True

            # Desactivo lo de frecuencia
            self.ids.freq_text.disabled = True
            self.ids.freq_input.disabled = True
            self.ids.freq_text_unidad.disabled = True
            self.ids.frec_precision.disabled = True

            # Deshabilito el seteo de componente o angulo
            self.ids.angcomp_text.disabled = True
            self.ids.angcomp_input.disabled = True
            self.ids.angcomp_seteo_angulo.disabled = True
            self.ids.angcomp_seteo_angulo_text.disabled = True
            self.ids.angcomp_seteo_capacitor.disabled = True
            self.ids.angcomp_seteo_c_text.disabled = True
            self.ids.angcomp_seteo_inductor.disabled = True
            self.ids.angcomp_seteo_l_text.disabled = True

########################################################################################################################
### Funcion para mover el punto dentro del smith #######################################################################
########################################################################################################################

    def move_point(self, x, y):                             # Le paso la pos x,y que quiero (Esta referido al centro del
                                                            #diagrama de smith utilizado)
        self.punto.posicion_x = x
        self.punto.posicion_y = y
        self.punto.move(self.ids.smith_img.parent.center)   # Como bien lo dice, mueve el punto a la pos x,y

########################################################################################################################
### Funciones para el arduino ##########################################################################################
########################################################################################################################

    # Funcion que llama al popup de arduino (de conexion)
    def arduino_popup(self):
        ArduinoConnectPopup(self.arduino_popup_cb)

    # Callback del popup de conexion de arduino
    def arduino_popup_cb(self, ar_sel):
        self.arduino_conectado = ar_sel                 # Sirve tanto como para mostar el nombre como para llamarlo

        # Mueve el stub a alguno de los dos extremos, o sea, los fines de carrera para tener una referencia.
#        s = serial.Serial(self.arduino_conectado)
#        s.write('I20000U\n')
#        #print(s.readline())
#        s.close()

    def arduino_lectura(self):
        if self.arduino_conectado != "Desconectado":
            try:
                s=serial.Serial(self.arduino_conectado)
                bytesToRead = s.inWaiting()
                self.arduino_read = s.read(bytesToRead)
                s.close()
            except (OSError, serial.SerialException):
                self.arduino_read = ""
                return

    # Chequea la conexion del arduino
    def arduino_test_connection(self):
        if self.arduino_conectado != "Desconectado":        # Si esta desconectado, no hace falta chequear conn
            try:
                s = serial.Serial(self.arduino_conectado)
                s.close()
            except (OSError, serial.SerialException):       # En caso que no pueda conectarme con el arduino
                self.arduino_conectado = "Desconectado"
#                self.start = 0

########################################################################################################################
### Funciones referidas al stub ########################################################################################
########################################################################################################################

    # Chequea el stub elegido y, en base a eso, habilita o deshabilita widgets
    def stubsel_check(self):
        if self.ids.stub_sel_id.text == "Seleccionar" or self.start == 1:
            self.ids.stub_borrar_id.disabled = True
        else:
            self.ids.stub_borrar_id.disabled = False

    # Chequea que se haya seleccionado un stub
    def stub_check(self):  # Usado por cada uno de los modos
        if self.ids.stub_sel_id.text == "Seleccionar":  # Habria que ver tambien cuando ingrese uno nuevo
            txt = 'Seleccione un stub para continuar'
            ErrorPopup(txt)
            return -1
        return 0

    # Funcion que se llama al elegir un stub, si es "Nuevo", abre un Popup como para agregarlo
    def on_stub_selected(self):
        self.ids.frec_precision.text = "Seleccionar"
        if self.ids.stub_sel_id.text == "Nuevo":                    # Si quiero agregar un nuevo stub, popup para eso
            NewStubPopup(self.stub_new_popup_cb,self.mode_state)
        else:
            self.stub_sel = self.ids.stub_sel_id.text               # Esto se ejecuta luego de tocar "Nuevo" tambien
#            #print(self.stub_sel)

    # Callback que agrega el stub nuevo a la lista
    def stub_new_popup_cb(self, stub_name):
        if stub_name != "Seleccionar":
            self.basedatos.agregar_stub(stub_name)
        self.ids.stub_sel_id.text = stub_name

    # Cuando elijo algo del spinner del stub...
    def on_stub_spinner_clicked(self):
        aux = self.basedatos.listar("stub","nombre")    # Muestro lo que tiene la clase "stub"
        self.ids.stub_sel_id.values=[]
        for i in range(0,len(aux)):                     # Cargo los stubs encontrados para que puedan ser mostrados
            self.ids.stub_sel_id.values.append(aux[i][0])
        self.ids.stub_sel_id.values.append('Nuevo')     # Agrego el boto Nuevo en caso de que quiera agregase uno nuevo

    # Da opciones para quitar o agregar un nuevo stub
    def stub_borrar(self):
        StubDeletePopup(self.stub_borrar_cb)

    # Borrar stub
    def stub_borrar_cb(self, borrar):
        if borrar:
            # Borro el stub
            self.basedatos.borrar_stub(self.ids.stub_sel_id.text)
            self.ids.stub_sel_id.text = "Seleccionar"

########################################################################################################################
### Funciones para el VNA ##############################################################################################
########################################################################################################################

    # Chequea si el vna se desconecto o si no
    def vna_test_connection(self):                          # Mismo principio que el de arduino
        if self.vna_conectado != "Desconectado":
            try:
#                inst_test = self.rm.open_resource(self.vna_conectado)
                a = self.inst.query("*IDN?")
#                inst.close()
            except visa.VisaIOError:
                self.vna_conectado = "Desconectado"
                self.vna_showname = "Desconectado"

    # Inicializa el VNA cuando comienza con la calibracion
    def vna_init(self):
        try:
#            inst = self.rm.open_resource(str(self.vna_conectado))
    #        #print(inst.query("*IDN?"))
            self.inst.write("INST:SEL 'NA'")
            self.inst.write("CALC:FORM SMIT")
            self.inst.write("CALC:PAR:COUN 1")
            self.inst.write("AVER:COUN 1")

            # En base a que puerto tenga elegido, seteo S11 o S22
            if self.ids.calibracion_seteo_puerto1.active:
                self.inst.write("CALC:PAR1:DEF S11")
            else:
                self.inst.write("CALC:PAR1:DEF S22")
            ##############################################################
            self.inst.write("CALC:MARK1 NORM")
#            inst.close()
        except visa.VisaIOError:                                            # Si no se puede hacer, es que se dc o algo
            return -1
        return 0

    # Para que se centre en alguna frecuencia especifica
    def vna_setfreq(self,frec_inicial,frec_final,frec_sweep):
        try:
#            inst = self.rm.open_resource(str(self.vna_conectado))
            self.inst.write(str("FREQ:STAR %s" % frec_inicial))
            self.inst.write(str("FREQ:STOP %s" % frec_final))
#            if frec_sweep != 0:
            self.inst.write(str("SWE:POIN %s" % frec_sweep))
#            inst.close()
        except:
            return -1
        return 0

    # Lee el dato del VNA, e imprime modulo, angulo y componente en pantalla
    def vna_lectura(self):
        try:
#            inst = self.rm.open_resource(self.vna_conectado)
            measure = self.inst.query_ascii_values("CALC:SEL:DATA:SDAT?")        # Para leer real imag
            #print measure
#            inst.close()
        except visa.VisaIOError:                                            # Si no se puede hacer, es que se dc o algo
            return -1

        #mediciones_vna = []
        mediciones_vna_ReIm = []
        measure_real = []
        measure_img = []
        for i in range(0, len(measure)):                                    # Lo separo en real e img
            if (i % 2) == 1:
                measure_img.append(measure[i])
            else:
                measure_real.append(measure[i])

        prom_measure_real = sum(measure_real) / len(measure_real)           # Hago el promedio de ambas partes
        prom_measure_img = sum(measure_img) / len(measure_img)
        mediciones_vna_ReIm.append(prom_measure_real)
        mediciones_vna_ReIm.append(prom_measure_img)
        div = prom_measure_img / prom_measure_real                          # Hago la div de ambas
        ang_aux = round(math.degrees(math.atan(div)), 2)                    # Calculo el angulo
        if prom_measure_real > 0 and prom_measure_img > 0:                  # Correccion del angulo para tenerlo de
                                                                            #0 a 360 grados
            ang = ang_aux
        elif prom_measure_real < 0 < prom_measure_img:
            ang = 180 + ang_aux
        elif prom_measure_real < 0 and prom_measure_img < 0:
            ang = 180 + ang_aux
        else:
            ang = 360 + ang_aux

        # Guardo parte real e imaginaria en variables propias de Main para usarlas luego
        self.measure_real = prom_measure_real
        self.measure_img = prom_measure_img

        # Esto es mas que nada para mostrar en tiempo real como cambian los valores medidos
        mod = round(math.sqrt(math.pow(prom_measure_real, 2) + math.pow(prom_measure_img, 2)), 4)
        ang = round(ang, 2)
        #mediciones_vna.append(mod)
        #mediciones_vna.append(ang)
        self.angulo_out = str("ANG= %s" % ang)                      # Lo que va a imprimir con el angulo
        self.modulo_out = str("MOD= %s" % mod)                      # Lo que va a imprimir con el modulo

        s_complex = complex(prom_measure_real, prom_measure_img)            # Paso la medicion a compleja
        z_aux = (1 + s_complex) / (1 - s_complex) * 50                      # Calculo la impedancia
        if prom_measure_img < 0:                                            # Imprime la L o C en base a la freq
            z_posta = -1 / (z_aux.imag * 2 * math.pi * pow(10, 9))
            self.z_out = str("COMP: C = %sF" % si_format(z_posta, precision=2))
        else:
            z_posta = z_aux.imag / (2 * math.pi * pow(10, 9))
            self.z_out = str("COMP: L = %sH" % si_format(z_posta, precision=2))

        self.move_point(round(prom_measure_real * 122, 0), round(prom_measure_img * 122, 0))        # Mueve el punto
        #print mediciones_vna_ReIm
        return mediciones_vna_ReIm

    # Popup del VNA
    def vna_popup(self):
        VNAConnectPopup(self.vna_popup_cb)

    # Callback del popup del VNA
    def vna_popup_cb(self, vna_sel, showname):
        self.vna_showname = showname                    # El nombre que va a mostrar en la pantalla del equipo
        self.vna_conectado = vna_sel                    # Aca esta guardado el comando que se usa para abrir el vna

########################################################################################################################
### Funcion correspondiente al boton "Comenzar" ########################################################################
########################################################################################################################

    def start_fnc(self):
        start_switch = {0: self.mode0_start_fnc,        # Una especie de switch/case.
                        1: self.mode1_start_fnc,
                        2: self.mode2_start_fnc,
                        3: self.mode3_start_fnc
                        }
        #        self.start = 1
        if self.mode_state < 2:
            self.inst = self.rm.open_resource(self.vna_conectado)
            self.vna_test_connection()
        self.arduino_test_connection()
        self.serial_count = 0
        start_switch[self.mode_state]()                 # Elijo que ejecutar en base al estado de mode
        if self.start == 1:
            self.serie_arduino.port = self.arduino_conectado
            self.serie_arduino.baudrate = 9600
            self.serie_arduino.timeout = 0.5
            self.serie_arduino.open()
        else:
            if self.mode_state < 2:
                self.inst.close()

########################################################################################################################
### Funciones correspondientes a cada modo de operacion al tocar el boton "Comenzar" ###################################
########################################################################################################################

### Mode0 ##############################################################################################################

    # Funcion correspondiente al modo "Calibracion de precision"
    def mode0_start_fnc(self):
        #print("modo0")

        # Chequeo el estado de conexion tanto del VNA como del Arduino
        if self.vna_conectado == "Desconectado":
            txt = 'VNA desconectado'
            ErrorPopup(txt)
            self.start = 0                              # Para que no siga ejecutandose
            return

        if self.arduino_conectado == "Desconectado":
            txt = "Arduino desconectado"
            ErrorPopup(txt)
            self.start = 0                              # Para que no siga ejecutandose
            return

        # Me fijo si hay stub levantado, sino putea
        stub_check = self.stub_check()
        if stub_check == -1:
            #print(stub_check)
            self.start = 0
            return

        # Me fijo si la frecuencia elegida es correcta, sino putea
        freq_check = self.freq_input_check()                        # Si me devuelve -1, quiere decir que estaba mal!
        if freq_check == -1:
            #print(freq_check)
            self.start = 0                                          # Habria que ver si sigo usando esto
            return
        self.long_onda = 2.99792458/(freq_check*10)
        if freq_check < 1:
            self.freq_start_sel = "%sE6" % int(freq_check*1000)
        else:
            self.freq_start_sel = "%sE9" % int(freq_check)
        #print(self.freq_start_sel)

        # Si llego hasta aca, entonces ya estamos en condiciones de arrancar
        vna_init_check = self.vna_init()                            # Inicializo el vna para medir
        if vna_init_check == -1:
            txt = "Se rompio en el init"
            ErrorPopup(txt)
            self.start = 0
            return

        # Lo pongo en una frecuencia especifica para medir
        vna_setfreq = self.vna_setfreq(self.freq_start_sel, self.freq_start_sel, "10")
        if vna_setfreq == -1:
            txt = "Se rompio seteando la frecuencia"
            ErrorPopup(txt)
            self.start = 0
            return

        freq_cant_aux = self.basedatos.listar_frecuencias(self.ids.stub_sel_id.text)
        for i in range(0,len(freq_cant_aux)):
            if float(self.ids.freq_input_text.text) == float(freq_cant_aux[i][0]):
                MismaFrecPopup(self.rw_frec)
                self.serie_arduino.close()
                self.inst.close()
                return

        self.mode0_state = 0
        self.start = 1

    def rw_frec(self,args):
        if args == 1:
            self.mode0_state = 0
            self.start = 1
            self.serie_arduino.port = self.arduino_conectado
            self.serie_arduino.baudrate = 9600
            self.serie_arduino.timeout = 0.5
            self.serie_arduino.open()
            self.inst = self.rm.open_resource(self.vna_conectado)
        else:
            self.mode0_state = 0
            self.start = 0

### Mode1 ##############################################################################################################

    # Funcion correspondiente al modo "Calibracion rapida"
    def mode1_start_fnc(self):
        #print("modo1")

        # Chequeo el estado de conexion tanto del VNA como del Arduino
        if self.vna_conectado == "Desconectado":
            txt = 'VNA desconectado'
            ErrorPopup(txt)
            self.start = 0                              # Para que no siga ejecutandose
            return

        if self.arduino_conectado == "Desconectado":
            txt = "Arduino desconectado"
            ErrorPopup(txt)
            self.start = 0                              # Para que no siga ejecutandose
            return

        # Me fijo si hay stub levantado, sino putea
        stub_check = self.stub_check()
        if stub_check == -1:
            #print(stub_check)
            self.start = 0
            return

        vna_init_check = self.vna_init()                            # Inicializo el vna para medir
        if vna_init_check == -1:
            txt = "Se rompio en el init"
            ErrorPopup(txt)
            self.start = 0
            return

        # Lo pongo en una frecuencia especifica para medir
        vna_setfreq = self.vna_setfreq("1E9","8E9","8")             # Barro de 1 a 8 GHz con un sweep de 1GHz
        if vna_setfreq == -1:
            txt = "Se rompio seteando la frecuencia"
            ErrorPopup(txt)
            self.start = 0
            return

        stubs_calrapida_aux = self.basedatos.listar_frecuencias(self.ids.stub_sel_id.text)
        #print len(stubs_calrapida_aux)
        if len(stubs_calrapida_aux) != 0:
            RapidaPopup(self.rw_rapida)
            self.serie_arduino.close()
            self.inst.close()
            return

        #print self.vna_conectado
        self.mode1_state = 0
        self.start = 1

    def rw_rapida(self,args):
        if args == 1:
            self.mode1_state = 0
            self.start = 1
            self.serie_arduino.port = self.arduino_conectado
            self.serie_arduino.baudrate = 9600
            self.serie_arduino.timeout = 0.5
            #print self.vna_conectado
            self.serie_arduino.open()
            self.inst = self.rm.open_resource(self.vna_conectado)
        else:
            #print self.vna_conectado
            self.mode1_state = 0
            self.start = 0

### Mode2 ##############################################################################################################

    # Funcion correspondiente al modo "Lazo abierto de precision"
    def mode2_start_fnc(self):
        #print("modo2")

        # Chequeo el estado de conexion del Arduino
        if self.arduino_conectado == "Desconectado":
            txt = "Arduino desconectado"
            ErrorPopup(txt)
            self.start = 0                              # Para que no siga ejecutandose
            return

        # Me fijo si hay stub levantado, sino putea
        stub_check = self.stub_check()
        if stub_check == -1:
            #print(stub_check)
            self.start = 0
            return

        if self.ids.frec_precision.text == "Seleccionar":
            txt = "Seleccione una frecuencia de calibracion valida"
            ErrorPopup(txt)
            self.start = 0
            return
        else:
            # Guardo las frecuencias de la calibracion adv
            frecuencia = float(string.replace(self.ids.frec_precision.text," GHz",""))
            self.freq_usada = frecuencia
            lectura_adv = self.basedatos.lectura_calibracion_adv(self.ids.stub_sel_id.text, frecuencia)
            # Me fijo si la frecuencia elegida es correcta, sino putea
            pasos = lectura_adv[len(lectura_adv)-1]
            pasos = pasos[0]
            #print lectura_adv
            #print pasos
            self.measure_real_inicial = lectura_adv[0][0]
            self.measure_img_inicial = lectura_adv[0][1]

            if self.ids.angcomp_seteo_angulo.active:
                self.mode3_componente_elegido = ang_sel_fnc(self.ids.angcomp_input_text.text)
                if self.mode3_componente_elegido == -1:
                    self.start = 0
                    return
                else:
                    self.ang_sel = self.mode3_componente_elegido
                    salir = 0
                    i = 0
                    #img_siguiente = 0
                    #real_siguiente = 0
                    #img_anterior = 0
                    #real_anterior = 0


                    while salir == 0:
                        ang_aux = math.degrees(math.atan(lectura_adv[i][1]/lectura_adv[i][0]))

                        if lectura_adv[i][0] > 0 and lectura_adv[i][1] > 0:  # Correccion del angulo para tenerlo de
                            # 0 a 360 grados
                            ang_aux = ang_aux
                        elif lectura_adv[i][0] < 0 < lectura_adv[i][1]:
                            ang_aux = 180 + ang_aux
                        elif lectura_adv[i][0] < 0 and lectura_adv[i][1] < 0:
                            ang_aux = 180 + ang_aux
                        else:
                            ang_aux = 360 + ang_aux
                        if i == 0:
                            ang_init = ang_aux
                            #print "angulo inicial"
                            #print ang_init
                            ang_sel_relativo = ang_init - self.ang_sel
                            if ang_sel_relativo < 0:
                                ang_sel_relativo = 360 + ang_sel_relativo
                            #print "desplazamiento angular relativo"
                            #print ang_sel_relativo
                        ang_aux_relativo = ang_init - ang_aux
                        if ang_aux_relativo < 0:
                            ang_aux_relativo = 360 + ang_aux_relativo
                        #print ang_aux_relativo
                        if ang_sel_relativo > ang_aux_relativo:
                            real_anterior = lectura_adv[i][0]
                            img_anterior = lectura_adv[i][1]
                            i += 1
                            real_siguiente = lectura_adv[i][0]
                            img_siguiente = lectura_adv[i][1]
                        else:
                            salir = 1

                    ang_aux = math.degrees(math.atan(img_anterior / real_anterior))
                    if real_anterior > 0 and img_anterior > 0:  # Correccion del angulo para tenerlo de
                        # 0 a 360 grados
                        ang_aux = ang_aux
                    elif real_anterior < 0 < img_anterior:
                        ang_aux = 180 + ang_aux
                    elif real_anterior < 0 and img_anterior < 0:
                        ang_aux = 180 + ang_aux
                    else:
                        ang_aux = 360 + ang_aux
                    #print "Angulo antes"
                    ang_antes = ang_aux
                    #print ang_antes
                    #print "Angulo seleccionado"
                    #print self.ang_sel
                    ang_aux = math.degrees(math.atan(img_siguiente / real_siguiente))
                    if real_siguiente > 0 and img_siguiente > 0:  # Correccion del angulo para tenerlo de
                        # 0 a 360 grados
                        ang_aux = ang_aux
                    elif real_siguiente < 0 < img_siguiente:
                        ang_aux = 180 + ang_aux
                    elif real_siguiente < 0 and img_siguiente < 0:
                        ang_aux = 180 + ang_aux
                    else:
                        ang_aux = 360 + ang_aux
                    #print "Angulo despues"
                    ang_despues = ang_aux
                    #print ang_despues
                    #print "Pasos para minimo"
                    pasos_min = i*pasos
                    #print pasos_min
                    self.pasos_mover = (i + abs(ang_antes-self.ang_sel)/abs(ang_antes-ang_despues))*pasos
                    #print self.pasos_mover
                    self.measure_real = math.sqrt(pow((img_anterior+img_siguiente)/2,2)+pow((real_anterior+real_siguiente)/2,2))*math.cos(math.pi*self.ang_sel/180)
                    self.measure_img = math.sqrt(pow((img_anterior+img_siguiente)/2,2)+pow((real_anterior+real_siguiente)/2,2))*math.sin(math.pi*self.ang_sel/180)
            else:
                impedancia_aux = []
                real_smith_aux = []
                if self.ids.angcomp_seteo_capacitor.active:
                    self.mode3_componente_elegido = capa_sel_fnc(self.ids.angcomp_input_text.text)
                    if self.mode3_componente_elegido == -1:
                        self.start = 0
                        return
                    impedancia_aux = -1 / (self.mode3_componente_elegido * pow(10, -3) * 2 * math.pi * frecuencia * 50)

                if self.ids.angcomp_seteo_inductor.active:
                    self.mode3_componente_elegido = inductor_sel_fnc(self.ids.angcomp_input_text.text)
                    if self.mode3_componente_elegido == -1:
                        self.start = 0
                        return
                    impedancia_aux = self.mode3_componente_elegido * 2 * math.pi * frecuencia / 50

                salir = 0
                flag_imp_menor = 0
                i = 0
                while salir == 0:
                    Z_aux = 2*lectura_adv[i][1] / (pow(lectura_adv[i][1],2)+pow((1-lectura_adv[i][0]),2))
                    if i == 0:
                        Z_init = Z_aux
                        if (impedancia_aux - Z_init) < 0:
                            flag_imp_menor = 1
                    if impedancia_aux > Z_aux or flag_imp_menor == 1:
                        real_anterior = lectura_adv[i][0]
                        img_anterior = lectura_adv[i][1]
                        i += 1
                        if i >= (len(lectura_adv)-1):
                            txt = "Punto no valido"
                            ErrorPopup(txt)
                            self.start = 0
                            self.serie_arduino.close()
#                            self.inst.close()
                            return
                        real_siguiente = lectura_adv[i][0]
                        img_siguiente = lectura_adv[i][1]
                        Z_aux = 2 * lectura_adv[i][1] / (pow(lectura_adv[i][1], 2) + pow((1 - lectura_adv[i][0]), 2))
                        if(impedancia_aux > Z_aux):
                            flag_imp_menor = 0
                    else:
                        salir = 1

                #print i
                #print "X antes"
                X_antes = 2 * img_anterior / (pow(img_anterior, 2) + pow((1 - real_anterior), 2))
                #print img_anterior
                #print real_anterior
                #print X_antes

                #print "X seleccionado"
                #print impedancia_aux

                #print "X despues"
                X_despues = 2 * img_siguiente / (pow(img_siguiente, 2) + pow((1 - real_siguiente), 2))
                #print X_despues

                #print "Pasos para minimo"
                pasos_min = i * pasos
                #print pasos_min

                self.pasos_mover = (i + abs(X_antes - impedancia_aux) / abs(X_antes - X_despues)) * pasos
                #print self.pasos_mover
                self.measure_real = real_anterior + abs(X_antes - impedancia_aux)*(real_siguiente - real_anterior) / abs(X_antes - X_despues)
                self.measure_img = img_anterior + abs(X_antes - impedancia_aux)*(img_siguiente - img_anterior) / abs(X_antes - X_despues)

            self.mode2_state = 0
            self.start = 1

### Mode3 ##############################################################################################################

    # Funcion correspondiente al modo "Lazo abierto rapido"
    def mode3_start_fnc(self):
        #print("modo3")

        # Chequeo el estado de conexion del Arduino
        if self.arduino_conectado == "Desconectado":
            txt = "Arduino desconectado"
            ErrorPopup(txt)
            self.start = 0                              # Para que no siga ejecutandose
            return

        # Me fijo si hay stub levantado
        stub_check = self.stub_check()
        if stub_check == -1:
            #print(stub_check)
            self.start = 0
            return

        # Guardo las frecuencias de la calibracion rapida
        lectura_calrapida = self.basedatos.lectura_calibracion_rapida(self.ids.stub_sel_id.text)

        # Si el tamanio del vector es 0, no existe la calibracion rapida para el stub seleccionado
        #print lectura_calrapida
        if len(lectura_calrapida) == 0:
            txt = "Realizar la calibracion rapida\npara el stub seleccionado"
            ErrorPopup(txt)
            self.start = 0
            return
        # En cambio, si existe la calibracion, extrapolo los pasos necesarios para el angulo determinado
        else:
            # Me fijo si la frecuencia elegida es correcta, sino putea
            lectura_calrapida = lectura_calrapida[0]
            freq_check = self.freq_input_check()                        # Si me devuelve -1, quiere decir que estaba mal!
            if freq_check == -1:
                #print(freq_check)
                self.start = 0                                          # Habria que ver si sigo usando esto
                return

        # HACER ESTOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOO
        #Bueno

        frec_cota_sup = 0
        frec_cota_inf = 0
        if freq_check >= 1:
            for i in range(1, 9, 1):
                #print i
                if freq_check >= i:
                    frec_cota_inf = i
            for i in range(8, 0, -1):
                #print i
                if freq_check <= i:
                    frec_cota_sup = i
            variacion = freq_check - int(freq_check)
        else:
            if freq_check == 0.85:
                frec_cota_inf = 0
                frec_cota_sup = frec_cota_inf
            else:
                frec_cota_sup = 1
                frec_cota_inf = 0
            variacion = (freq_check-0.85)/0.15

        if frec_cota_inf == frec_cota_sup:
            self.ROE = lectura_calrapida[19+frec_cota_inf*2]
            self.ANG_init = lectura_calrapida[20+frec_cota_inf*2]
            self.deltaROE = lectura_calrapida[1+frec_cota_inf*2]
            self.deltaANG = lectura_calrapida[2+frec_cota_inf*2]
        else:
            self.ROE = lectura_calrapida[19+frec_cota_inf*2] + (lectura_calrapida[19+frec_cota_sup*2]-lectura_calrapida[19+frec_cota_inf*2])*variacion
            self.ANG_init = lectura_calrapida[20+frec_cota_inf*2] + (lectura_calrapida[20+frec_cota_sup*2]-lectura_calrapida[20+frec_cota_inf*2])*variacion
            self.deltaROE = lectura_calrapida[1+frec_cota_inf*2] + (lectura_calrapida[1+frec_cota_sup*2]-lectura_calrapida[1+frec_cota_inf*2])*variacion
            self.deltaANG = lectura_calrapida[2+frec_cota_inf*2] + (lectura_calrapida[2+frec_cota_sup*2]-lectura_calrapida[2+frec_cota_inf*2])*variacion

        self.measure_real_inicial = self.ROE * math.cos(math.pi * self.ANG_init /180)
        self.measure_img_inicial = self.ROE * math.sin(math.pi * self.ANG_init /180)

        ROE_aux = self.ROE
        self.deltaANG = self.deltaANG*1.02
        #print "ROE:"
        #print self.ROE
        #print "ANG_init:"
        #print self.ANG_init
        #print "deltaROE:"
        #print self.deltaROE
        #print "deltaANG:"
        #print self.deltaANG

        # Busco entre que valores se encuentra la frecuencia elegida, cosa de determinar a cuanto equivale un paso

        if self.ids.angcomp_seteo_angulo.active:
            self.mode3_componente_elegido = ang_sel_fnc(self.ids.angcomp_input_text.text)
            if self.mode3_componente_elegido == -1:
                self.start = 0
                return
            else:
                self.ang_sel = self.mode3_componente_elegido
        else:
            impedancia_aux = []
            real_smith_aux = []
            if self.ids.angcomp_seteo_capacitor.active:
                self.mode3_componente_elegido = capa_sel_fnc(self.ids.angcomp_input_text.text)
                if self.mode3_componente_elegido == -1:
                    self.start = 0
                    return
                impedancia_aux = 1/(self.mode3_componente_elegido*pow(10, -3)*2*math.pi*self.freq_input_check()*50)

            if self.ids.angcomp_seteo_inductor.active:
                self.mode3_componente_elegido = inductor_sel_fnc(self.ids.angcomp_input_text.text)
                if self.mode3_componente_elegido == -1:
                    self.start = 0
                    return
                impedancia_aux = self.mode3_componente_elegido*2*math.pi*self.freq_input_check()/50

            ang_ant = 360
            ang_actual = 0
            veces = 0
            while abs(ang_ant - ang_actual) > 0.01:
                veces += 1
                #print "cant de veces"
                #print veces
                #print "IMPEDANCIA_AUX"
                #print impedancia_aux
                a = 1 + pow(impedancia_aux, 2)
                b = -pow(impedancia_aux, 2)*(1+pow(self.ROE, 2))
                c = ((pow(1+pow(self.ROE, 2), 2)*pow(impedancia_aux, 2))/4-pow(self.ROE, 2))

                if pow(b, 2) < (4 * a * c):
                    txt = "Punto no valido"
                    ErrorPopup(txt)
                    self.start = 0
                    self.serie_arduino.close()
#                    self.inst.close()
                    return

                val1 = (-b + math.sqrt(pow(b, 2)-4*a*c))/(2*a)
                val2 = (-b - math.sqrt(pow(b, 2)-4*a*c))/(2*a)

                #print "vals"
                #print val1
                #print val2

                if val1 < val2:                 #Siempre descarta el valor mayor de los dos
                    real_smith_aux = val1
                else:
                    real_smith_aux = val2

                #print "REAL SMITH"
                #print real_smith_aux
                #print "self.ROE"
                #print self.ROE
                img_smith_aux = math.sqrt(self.ROE*self.ROE-real_smith_aux*real_smith_aux)
                #print img_smith_aux
                ang_aux = math.degrees(math.atan(img_smith_aux/real_smith_aux))  # Calculo el angulo
                #print ang_aux
                if real_smith_aux > 0 and img_smith_aux > 0:    # Correccion del angulo para tenerlo de
                                                                # 0 a 360 grados
                    self.ang_sel = ang_aux
                elif real_smith_aux < 0 < img_smith_aux:
                    self.ang_sel = 180 + ang_aux
                elif real_smith_aux < 0 and img_smith_aux < 0:
                    self.ang_sel = 180 + ang_aux
                else:
                    self.ang_sel = 360 + ang_aux

                if self.ids.angcomp_seteo_capacitor.active:
                    self.ang_sel = 360 - self.ang_sel
                ang_mov = self.ANG_init - self.ang_sel
                if ang_mov < 0:
                    ang_mov = 360 + ang_mov
                #print "Ang mover"
                #print ang_mov
                ang_ant = ang_actual
                ang_actual = self.ang_sel

                self.ROE = ROE_aux - self.deltaROE * ang_mov / self.deltaANG
                #print "diferencia ang"
                #print (ang_actual - ang_ant)
                if veces > 20:
                    ang_actual = ang_ant



        #print self.ang_sel
        self.measure_real = self.ROE * math.cos(math.pi * self.ang_sel / 180)
        self.measure_img = self.ROE * math.sin(math.pi * self.ang_sel / 180)

        self.mode3_state = 0
        self.start = 1


########################################################################################################################
### Funciones para corroborar que los parametros esten bien seteados (cada modo llamara a cuales corresponda) ##########
########################################################################################################################

    # Corrobora que el valor ingresado de frecuencia a calibrar sea valido, devolviendo su valor si es valido
    #  o -1 si es invalido
    def freq_input_check(self):             # Posibles modos -> 0: Calibracion de precision
                                            #                -> 3: Lazo abierto rapido
        error = 0
        aux_freq = 0
        aux = self.ids.freq_input_text.text
        # Me fijo que este en los valores adecuados y que ademas sea un digito valido
        if aux.replace('.', '', 1).isdigit():                   # Primero me fijo si esta bien el numero de por si
            aux_freq = round(float(aux), 3)
            if not(0.84 <= aux_freq <= 8):                      # Luego si se encuentra dentro del rango
                error = 1
        else:
            error = 1

        if error:
            txt = 'Frecuencia no valida.\n Valores aceptados entre 0.84GHz y 8GHz'
            ErrorPopup(txt)
            return -1
        else:
            return aux_freq

    def on_frec_spinner_selected(self):
        aux = self.ids.frec_precision.text
        if aux != "Seleccionar":
            self.freq_precision_sel = float(string.replace(aux," GHz",""))      # Para sacar el " GHz"
#        #print(self.freq_precision_sel)

    def on_frec_spinner_clicked(self):
        self.ids.frec_precision.values = []
        if self.ids.stub_sel_id.text == "Seleccionar":
            txt = "Seleccione un stub para\npoder elegir la frecuencia"
            ErrorPopup(txt)
        else:
            #print "entro a frecuencias"
            aux = self.basedatos.listar_frecuencias(self.ids.stub_sel_id.text)
            #print aux
            for i in range(0, len(aux)):  # Cargo los stubs encontrados para que puedan ser mostrados
                self.ids.frec_precision.values.append(str(aux[i][0]) + " GHz")
#            self.ids.frec_precision.values = self.basedatos.listar_frecuencias(self.ids.stub_sel_id.text)

########################################################################################################################
### Funcion correspondiente al boton "Detener" #########################################################################
########################################################################################################################

    def stop_fnc(self):
        self.start = 0
        self.serie_arduino.write("STOP\n")
        a = self.serie_arduino.read(999)
        self.serie_arduino.close()
        if self.mode_state < 2:
            self.inst.close()

########################################################################################################################
### Para graficar el punto #############################################################################################
########################################################################################################################


class PuntoEnGrafico(Widget):

    # El grafico del smith utilizado tiene 244 "pasos" de diametro
    posicion_x = NumericProperty(0)
    posicion_y = NumericProperty(0)
    posicion = ReferenceListProperty(posicion_x, posicion_y)

    def move(self,args):
        self.pos = Vector(self.posicion) + args - (3,3)         # Correccion muy burda, es en base a la figura

########################################################################################################################
### MainApp y '__main__' ###############################################################################################
########################################################################################################################


class MainApp(App):

    def build(self):
        self.title = ""
        return Main()


if __name__ == '__main__':
    MainApp().run()
