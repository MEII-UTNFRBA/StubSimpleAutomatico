from general_popups import ErrorPopup

########################################################################################################################
### Funciones correspondientes al ang/comp elegido estando en lazo abierto #############################################

# Funcion que verifica el valor ingresado como angulo


def ang_sel_fnc(args):

    ang = -1                                                # Valor inicial
    # Me fijo si el numero sin coma ni signo corresponde a un digito valido
    if args.lstrip('-').replace('.', '', 1).isdigit():
        aux_ang = float(args)
        # Esto es para que el angulo insertado quede entre -360 y 360 grados
        if float(aux_ang) > 360:
            while aux_ang > 360:
                aux_ang -= 360
        elif float(aux_ang) < -360:
            while aux_ang < -360:
                aux_ang += 360
        # Esto es para que el angulo insertado quede entre 0 y 360 grados
        if aux_ang < 0:
            ang = 360 + aux_ang
        else:
            ang = aux_ang
        if ang == 360:                  # Como 360 es lo mismo que 0, lo dejamos en 0
            ang = 0
    # En caso que no sea un digito valido
    else:
        txt = 'Angulo no valido'
        ErrorPopup(txt)
        ang = -1                                            # Hubo un error
    return float(ang)


# Funcion que verifica el valor ingresado como capacidad


def capa_sel_fnc(aux):
    capa = -1
    if aux.replace('.', '', 1).isdigit():
        capa = aux                                          # Hacer algo con esto
    else:
        txt = 'Capacitor no valido'
        ErrorPopup(txt)
        capa = -1
    return float(capa)

# Funcion que verifica el valor ingresado como inductancia


def inductor_sel_fnc(aux):
    inductor = -1
    if aux.replace('.', '', 1).isdigit():
        inductor = aux                                      # Hacer algo con esto
    else:
        txt = 'Inductancia no valida'
        ErrorPopup(txt)
        inductor = -1
    return float(inductor)
