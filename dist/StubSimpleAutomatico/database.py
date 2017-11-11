import sqlite3
import sys


class DataBase:

    def __init__(self):
        self._conn = None
        self.aux = ""

    def conectar(self):
        '''
            realiza la conexion a la base de datos
            retorna True si la conexion fue exitosa
        '''
        try:
            self._conn = sqlite3.connect('stubsimpleauto.db')
            return True
        except:
            #print sys.exc_info()[1]
            return False

    def _verifica_conexion(self):
        '''
            verifica que se haya realizado una conexion a la base de datos
            retorna True si ya se realizo la conexion
        '''
        if not self._conn:
            #print "Error. Todavia no se ha conectado a la base de datos"
            return False
        return True

    def init(self):
        if not self._verifica_conexion():
            return False
        cur = self._conn.cursor()
        #print("Base de datos abierta")
        cur.execute("PRAGMA table_info(stub)")
        data = cur.fetchall()
        #print(data)
        if len(data) == 0:
            #print("Tabla vacia")
            cur.execute("""
            CREATE TABLE stub(
            stub_id         INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre          TEXT    NOT NULL,
            cal_rapid_id    INT
            )""")
            cur.execute("""
            CREATE TABLE cal_rapid(
            cal_rapid_id    INTEGER PRIMARY KEY AUTOINCREMENT,
            cal_085r            REAL,
            cal_085i            REAL,
            cal_1r              REAL,
            cal_1i              REAL,
            cal_2r              REAL,
            cal_2i              REAL,
            cal_3r              REAL,
            cal_3i              REAL,
            cal_4r              REAL,
            cal_4i              REAL,
            cal_5r              REAL,
            cal_5i              REAL,
            cal_6r              REAL,
            cal_6i              REAL,
            cal_7r              REAL,
            cal_7i              REAL,
            cal_8r              REAL,
            cal_8i              REAL,
            cal_00r             REAL,
            cal_00i             REAL,
            cal_01r             REAL,
            cal_01i             REAL,
            cal_02r             REAL,
            cal_02i             REAL,
            cal_03r             REAL,
            cal_03i             REAL,
            cal_04r             REAL,
            cal_04i             REAL,
            cal_05r             REAL,
            cal_05i             REAL,
            cal_06r             REAL,
            cal_06i             REAL,
            cal_07r             REAL,
            cal_07i             REAL,
            cal_08r             REAL,
            cal_08i             REAL
            )""")
            cur.execute("""
            CREATE TABLE cal_precision(
            cal_precision_id    INTEGER PRIMARY KEY AUTOINCREMENT,
            stub_id             INT,
            frecuencia          REAL,
            pasos               INT
            )""")
            cur.execute("""
            CREATE TABLE medicion_precision(
            cal_precision_id    INT,
            valor_real          REAL,
            valor_img           REAL,
            valor_id            INT
            )""")
            self._conn.commit()
        cur.execute("PRAGMA table_info(stub)")
        data = cur.fetchall()
        #print(data)
        cur.close()

    def listar(self, tabla, campo):
        if not self._verifica_conexion():
            return False
        error = False
        try:
            cur = self._conn.cursor()
            cur.execute("SELECT %s FROM %s" % (campo,tabla))
            return cur.fetchall()
        except:
            #print sys.exc_info()[1]
            error = True
        finally:
            cur.close()
        return error

    def agregar_stub(self,nombre):
        cur = self._conn.cursor()
        cur.execute("SELECT stub_id FROM stub WHERE nombre='%s'"% nombre)
        stub_id = cur.fetchone()
        if stub_id is None:
            cur.execute("INSERT INTO stub(nombre) VALUES (?)", (nombre,))
            self._conn.commit()
        cur.close()

    def agregar_calibracion_rapida(self,calibracion,stub):
        datos = []
        cur = self._conn.cursor()
        cur.execute("SELECT cal_rapid_id FROM stub WHERE nombre='%s'"% stub)
        cal_rapid_id = cur.fetchone()
        if cal_rapid_id[0] is None:
            datos.extend(calibracion)
            cur.execute("""INSERT INTO cal_rapid(cal_085r,
                        cal_085i,
                        cal_1r,
                        cal_1i,
                        cal_2r,
                        cal_2i,
                        cal_3r,
                        cal_3i,
                        cal_4r,
                        cal_4i,
                        cal_5r,
                        cal_5i,
                        cal_6r,
                        cal_6i,
                        cal_7r,
                        cal_7i,
                        cal_8r,
                        cal_8i,
                        cal_00r,
                        cal_00i,
                        cal_01r,
                        cal_01i,
                        cal_02r,
                        cal_02i,
                        cal_03r,
                        cal_03i,
                        cal_04r,
                        cal_04i,
                        cal_05r,
                        cal_05i,
                        cal_06r,
                        cal_06i,
                        cal_07r,
                        cal_07i,
                        cal_08r,
                        cal_08i) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", (datos))
            self._conn.commit()
            cur.execute("SELECT MAX(cal_rapid_id) FROM cal_rapid")
            cal_rapid_id = cur.fetchone()
            cur.execute("UPDATE stub SET cal_rapid_id=? WHERE nombre = '%s'"%stub, (cal_rapid_id))
            self._conn.commit()
        else:
            datos.extend(calibracion)
            datos.append(cal_rapid_id[0])
            cur.execute("""UPDATE cal_rapid SET 
                        cal_085r=?,
                        cal_085i=?,
                        cal_1r=?,
                        cal_1i=?,
                        cal_2r=?,
                        cal_2i=?,
                        cal_3r=?,
                        cal_3i=?,
                        cal_4r=?,
                        cal_4i=?,
                        cal_5r=?,
                        cal_5i=?,
                        cal_6r=?,
                        cal_6i=?,
                        cal_7r=?,
                        cal_7i=?,
                        cal_8r=?,
                        cal_8i=?,
                        cal_00r=?,
                        cal_00i=?,
                        cal_01r=?,
                        cal_01i=?,
                        cal_02r=?,
                        cal_02i=?,
                        cal_03r=?,
                        cal_03i=?,
                        cal_04r=?,
                        cal_04i=?,
                        cal_05r=?,
                        cal_05i=?,
                        cal_06r=?,
                        cal_06i=?,
                        cal_07r=?,
                        cal_07i=?,
                        cal_08r=?,
                        cal_08i=? 
                        WHERE cal_rapid_id=?""", (datos))
            self._conn.commit()
        cur.close()

    def agregar_calibracion_adv(self, calibracion, stub, frecuencia, pasos):
        datos = []
        cur = self._conn.cursor()
        #print stub
        cur.execute("SELECT stub_id FROM stub WHERE nombre='%s'"% stub)
        stub_id = cur.fetchone()
        #print stub_id
        datos.extend(stub_id)
        datos.append(frecuencia)
        cur.execute("SELECT cal_precision_id FROM cal_precision WHERE stub_id=? AND frecuencia=?", datos)
        cal_precision_id = cur.fetchone()
        #print "precision_id"
        #print cal_precision_id
        if cal_precision_id is None:
            #print "entro lalalala"
            datos.append(pasos)
            cur.execute("INSERT INTO cal_precision(stub_id,frecuencia,pasos) VALUES (?,?,?)", datos)
            self._conn.commit()
            datos = []
            datos.extend(stub_id)
            datos.append(frecuencia)
            cur.execute("SELECT cal_precision_id FROM cal_precision WHERE stub_id=? AND frecuencia=?", datos)
            cal_precision_id = cur.fetchone()
        else:
            datos=[]
            datos.append(frecuencia)
            datos.append(pasos)
            datos.extend(cal_precision_id)
            cur.execute("UPDATE cal_precision SET frecuencia=?, pasos=? WHERE cal_precision_id=?", datos)
            self._conn.commit()
            cur.execute("DELETE FROM medicion_precision WHERE cal_precision_id=?", (cal_precision_id))
            self._conn.commit()
        for i in range(0, len(calibracion), 2):
            datos=[]
            datos.extend(cal_precision_id)
            datos.append(calibracion[i])
            datos.append(calibracion[i+1])
            datos.append(i)
            cur.execute("INSERT INTO medicion_precision VALUES (?,?,?,?)", datos)
        self._conn.commit()
        cur.close()

    def listar_stub(self):
        cur = self._conn.cursor()
        stub = cur.execute("SELECT nombre FROM stub")
        cur.close()
        return stub

    def listar_frecuencias(self,stub):
        cur = self._conn.cursor()
        cur.execute("SELECT stub_id FROM stub WHERE nombre = '%s'"%stub)
        data = cur.fetchone()
        #print(data)
        cur.execute("SELECT frecuencia FROM cal_precision WHERE stub_id=?", data)
        frecuencias = cur.fetchall()
        cur.close()
        return frecuencias

    def lectura_calibracion_rapida(self,stub):
        cur = self._conn.cursor()
        cur.execute("SELECT cal_rapid_id FROM stub WHERE nombre = '%s'"%stub)
        cal_rapid_id = cur.fetchone()
        if cal_rapid_id[0] is None:
            cur.close()
            mediciones = []
        else:
            cur.execute("SELECT * FROM cal_rapid WHERE cal_rapid_id=?", cal_rapid_id)
            mediciones = cur.fetchall()
            cur.close()
        return mediciones

    def lectura_calibracion_adv(self, stub, frecuencia):
        cur = self._conn.cursor()
        #print stub
        #print frecuencia
        cur.execute("""SELECT cal_precision_id FROM cal_precision WHERE frecuencia=? 
                    AND stub_id=(SELECT stub_id FROM stub WHERE nombre='%s')"""% stub, (frecuencia,))
        cal_precision_id = cur.fetchone()
        #print cal_precision_id
        if cal_precision_id is None:
            cur.close()
            mediciones =[]
        else:
            cur.execute("SELECT valor_real,valor_img FROM medicion_precision WHERE cal_precision_id=? ORDER BY valor_id", (cal_precision_id))
            mediciones = cur.fetchall()
            cur.execute("SELECT pasos FROM cal_precision WHERE cal_precision_id=?", (cal_precision_id))
            pasos = cur.fetchone()
            mediciones.append(pasos)
            cur.close()
        return mediciones

    def borrar_stub(self,stub):
        cur = self._conn.cursor()
        cur.execute("SELECT stub_id FROM stub WHERE nombre = '%s'" % stub)
        sutbid=cur.fetchone()
        cur.execute("SELECT cal_rapid_id FROM stub WHERE nombre = '%s'" % stub)
        rapidid=cur.fetchone()
        cur.execute("SELECT cal_precision_id FROM cal_precision WHERE stub_id = ?",  sutbid)
        medid=cur.fetchone()
        cur.execute("DELETE FROM stub WHERE nombre = '%s'" % stub)
        cur.execute("DELETE FROM cal_rapid WHERE cal_rapid_id = '%s'" % rapidid)
        cur.execute("DELETE FROM cal_precision WHERE stub_id = '%s'" % sutbid)
        cur.execute("DELETE FROM medicion_precision WHERE cal_precision_id = '%s'" % medid)
        self._conn.commit()
        cur.close()


if __name__ == '__main__':

    #calibracion = [0.9091683067694444, 0.9142188118199495, 0.9192693168704545, 0.9243198219209596, 0.9293703269714646, 0.9344208320219697, 0.9394713370724748, 0.9445218421229797, 0.9495723471734848, 0.9546228522239899]#, 0.9596733572744949, 0.964723862325, 0.969774367375505, 0.9748248724260101, 0.9798753774765151, 0.9849258825270202, 0.9899763875775253, 0.9950268926280302, 0.5076302857, -0.40395883, 0.1479687967, -0.902092551, 0.8680801161, 0.0946174308, 0.0575000514, 0.8695636264, -0.7148194136, 0.4295295225, -0.5441409758, -0.6198151377, 0.5232329087, -0.5847795969, 0.5301742837, -0.4013099851, -0.5918462693, 0.2646576207]
    calibracion = [1,2,3,4,5,6,7,8]
    nombre_stub = "Micho"

    clase_sqlite = DataBase()

    clase_sqlite.conectar()
    #clase_sqlite.init()
    #clase_sqlite.agregar_stub("MONGO")
#    clase_sqlite.listar("stub","nombre")
#    clase_sqlite.agregar_stub("Tongo")
#    clase_sqlite.listar("stub","nombre")
    #clase_sqlite.listar("cal_rapid")
    #mediciones = (1,2,3,5,8,13,21,34)
    #clase_sqlite.agregar_calibracion_rapida(mediciones, str("CHONGO"))
    #clase_sqlite.listar("stub")
#    _cal_5ghz = clase_sqlite.lectura_calibracion_rapida(str("CHONGO"))
#    #print(_cal_5ghz[0][5])
    #clase_sqlite.agregar_calibracion_rapida(calibracion, nombre_stub)
    #clase_sqlite.agregar_calibracion_adv(calibracion, nombre_stub, float(1), 40)
    #print clase_sqlite.lectura_calibracion_adv(nombre_stub, 1)