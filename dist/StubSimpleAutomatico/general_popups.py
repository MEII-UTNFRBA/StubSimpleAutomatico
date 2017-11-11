from kivy.properties import ObjectProperty, StringProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.popup import Popup
from serial_functions import serial_ports
from kivy.uix.textinput import TextInput
import visa


########################################################################################################################
### Popups #############################################################################################################

# Popup para agregar un nuevo stub


class NewStubPopup(Popup):

    def __init__(self,callback,mode):
        super(NewStubPopup, self).__init__()
        box = BoxLayout(orientation='vertical')
        if mode > 1:
            box.add_widget(Label(
                    text="No permitido para este modo"))
            self.title = 'Error'
            self.content = box
            self.size_hint = (0.4, 0.4)
            box.add_widget(Button(
                text="OK",
                on_press=lambda *args: NewStubPopup.on_enter(self,callback,1)))
        else:
            box.add_widget(Label(
                    text="Ingrese nombre del stub y presione 'Enter'"))
            self.title = 'Stub nuevo'
            self.content = box
            self.size_hint = (0.4, 0.4)
            self.txtinput = TextInput(multiline=False,on_text_validate=lambda *args: NewStubPopup.on_enter(self,callback,0))
            box.add_widget(self.txtinput)
            box.add_widget(Button(
                text="Cancelar",
                on_press=lambda *args: NewStubPopup.cancel(self,callback)))
        self.auto_dismiss = False
        self.open()

    def cancel(self,callback):
        callback(str("Seleccionar"))
        self.dismiss()

    def on_enter(self,callback,error):
        if error:
            callback("Seleccionar")
        else:
            callback(str(self.txtinput.text))
        self.dismiss()


# Popup para elegir el vna al cual conectarse


class VNAConnectPopup(Popup):

    vna_elegido = StringProperty()
    rm = visa.ResourceManager()

    def __init__(self,callback):
        super(VNAConnectPopup, self).__init__()
        self.vna_elegido = "Desconectado"               #HAY QUE SACARLO, esta solo para que no rompa Cancelar
        a = ObjectProperty()
        a = self.rm.list_resources(query=u'USB?*')
#        a = self.rm.list_resources()
#        #print(a)
        test = []
        inst_aux = []
        if len(a) > 0:
            for i in range(0,len(a)):
                test.append(1)
                try:
                    inst_test = self.rm.open_resource(str(a[i]))
                    var_aux = str(inst_test.query("*IDN?"))
                    inst_test.close()
                except visa.VisaIOError:
                    test[i] = 0

            for i in range(0,len(a)):
                if test[i] == 1:
                    inst_aux.append(a[i])
        if len(inst_aux) > 0:
            box = BoxLayout(orientation='vertical')
            for i in range(0, len(inst_aux)):
                inst = self.rm.open_resource(str(inst_aux[i]))
                var = str(inst.query("*IDN?"))
                texto = []
                haycoma = 0
                for j in range(0,len(var)):
                    if var[j] == ',':
                        haycoma = haycoma + 1
                    if haycoma == 2:
                        break
                    else:
                        texto.append(var[j])
                texto=''.join(texto)
                box.add_widget(Button(
                    text=texto,
                    on_press = lambda *args: VNAConnectPopup.vnasel(self, callback, inst_aux[i],texto)))
                inst.close()
            self.title = 'Seleccione un equipo'
            self.content=box
            self.size_hint=(0.4, 0.4)
        else:
            box = BoxLayout(orientation='vertical')
            box.add_widget(Label(text='No hay equipo conectado'))
            self.title = 'Error'
            self.content=box
            self.size_hint=(0.4, 0.4)
        box.add_widget(Button(
            text="Cancelar",
            on_press=lambda *args: VNAConnectPopup.cancel(self)))
        self.auto_dismiss = False
        callback("Desconectado","Desconectado")
        self.open()

    def cancel(self):
        self.dismiss()

    def vnasel(self,callback,vna_sel,showname):
        self.vna_elegido = vna_sel
        callback(self.vna_elegido,showname)               #Hay que ver si se rompe por esto
#        inst = rm.open_resource(str(vna_elegido))      #Hay que ver como hacer para que no se rompa
#        #print(str(self.vna_elegido))
#        inst = self.rm.open_resource(str(self.vna_elegido))
#        #print(inst.query("*IDN?"))
#        inst.write("INST:SEL 'NA'")
#        inst.write("CALC:FORM SMIT")
#        inst.write("CALC:PAR:COUN 1")
#        inst.write("CALC:PAR1:DEF S22")
#        inst.write("FREQ:STAR 1E9")
#        inst.write("FREQ:STOP 1E9")
#        inst.write("CALC:MARK1 NORM")
#        inst.write(":FREQ:CENT 803000")          #Para el DSA815 (SA)
#        inst.close()
        self.dismiss()


# Popup para elegir el puerto de arduino al cual conectarse


class ArduinoConnectPopup(Popup):

    puerto_arduino = StringProperty()

    def __init__(self,callback):
        super(ArduinoConnectPopup, self).__init__()
        self.puerto_arduino = "Mongo"
        a=serial_ports()
        if len(a) > 0:
            box = BoxLayout(orientation='vertical')
            for i in range(0, len(a)):
                box.add_widget(Button(
                    text=str(a[i]),
                    on_press=lambda *args: ArduinoConnectPopup.comsel(self, callback, a[i])))
            self.title = 'Seleccione un equipo'
            self.content = box
            self.size_hint = (0.4, 0.4)
        else:
            box = BoxLayout(orientation='vertical')
            box.add_widget(Label(text='No hay equipo conectado'))
            self.title = 'Error'
            self.content = box
            self.size_hint = (0.4, 0.4)
        box.add_widget(Button(
            text="Cancelar",
            on_press=lambda *args: ArduinoConnectPopup.cancel(self)))
        self.auto_dismiss = False
        callback("Desconectado")
        self.open()

    def cancel(self):
        self.dismiss()

    def comsel(self,callback,port_sel):
        self.puerto_arduino = port_sel          #Esta en caso de necesitarlo luego
        callback(self.puerto_arduino)
        self.dismiss()

# Popup que tira mensaje de error


class ErrorPopup(Popup):
    def __init__(self, txt):
        super(ErrorPopup, self).__init__()
        self.title = 'Error'
        content = BoxLayout(orientation='vertical')
        self.size_hint = (None,None)
        self.size = (300,200)
        self.auto_dismiss = False
        content.add_widget(Label(text=txt,
                                 halign='center'))
        content.add_widget(Button(text='Cerrar', on_press=self.dismiss))
        self.content = content
        self.open()

# Popup que pregunta por la eliminacion o no del stub seleccionado


class StubDeletePopup(Popup):
    def __init__(self, callback):
        super(StubDeletePopup, self).__init__()
        self.title = 'ADVERTENCIA'
        content = BoxLayout(orientation='vertical')
        self.size_hint = (None,None)
        self.size = (370,200)
        self.auto_dismiss = False
        content.add_widget(Label(text='Si borra el stub seleccionado, perdera todas\nlas mediciones guardadas del mismo. Continuar?',
                                 halign='center'))
        content.add_widget(Button(text='Aceptar', on_press=lambda *args: StubDeletePopup.stub_delete(self,callback,1)))
        content.add_widget(Button(text='Cancelar', on_press=lambda *args: StubDeletePopup.stub_delete(self,callback,0)))
        self.content = content
        self.open()

    def stub_delete(self,cb,args):
        cb(args)
        self.dismiss()


class MismaFrecPopup(Popup):
    def __init__(self, callback):
        super(MismaFrecPopup, self).__init__()
        self.title = 'ADVERTENCIA'
        content = BoxLayout(orientation='vertical')
        self.size_hint = (None, None)
        self.size = (370, 200)
        self.auto_dismiss = False
        content.add_widget(Label(
            text='Si realiza la calibracion a esta frecuencia,\nperdera la anterior realizada de la misma. Continuar?',
            halign='center'))
        content.add_widget(
            Button(text='Aceptar', on_press=lambda *args: MismaFrecPopup.frec_sobreescribir(self, callback, 1)))
        content.add_widget(
            Button(text='Cancelar', on_press=lambda *args: MismaFrecPopup.frec_sobreescribir(self, callback, 0)))
        self.content = content
        self.open()

    def frec_sobreescribir(self, cb, args):
        cb(args)
        self.dismiss()


class RapidaPopup(Popup):
    def __init__(self, callback):
        super(RapidaPopup, self).__init__()
        self.title = 'ADVERTENCIA'
        content = BoxLayout(orientation='vertical')
        self.size_hint = (None, None)
        self.size = (370, 200)
        self.auto_dismiss = False
        content.add_widget(Label(
            text='Si realiza la calibracion rapida del stub,\nperdera la anterior realizada del mismo. Continuar?',
            halign='center'))
        content.add_widget(
            Button(text='Aceptar', on_press=lambda *args: RapidaPopup.rw_rapida(self, callback, 1)))
        content.add_widget(
            Button(text='Cancelar', on_press=lambda *args: RapidaPopup.rw_rapida(self, callback, 0)))
        self.content = content
        self.open()

    def rw_rapida(self, cb, args):
        cb(args)
        self.dismiss()