# Importa los elementos definidos en modelo.py para mantener conectado el proyecto.
from modelo import (
    Callable,
    Cliente,
    ConflictoReserva,
    Decimal,
    ErrorOperacion,
    ErrorSistema,
    ErrorValidacion,
    Optional,
    RUTA_LOG,
    RecursoNoEncontrado,
    Reserva,
    SalidaSolicitada,
    Servicio,
    ServicioCapacitacion,
    ServicioConsultoria,
    ServicioMantenimiento,
    ServicioNoDisponible,
    a_decimal,
    date,
    datetime,
    formato_dinero,
    logger,
    re,
    registrar_error,
    timedelta,
)

# --------------------------- FUNCIONES DE ENTRADA -------------------------


def leer_entrada(mensaje: str) -> str:
    """Lee texto de consola y transforma fin de entrada en una salida controlada."""
    try:
        return input(mensaje).strip()
    except EOFError as exc:
        # EOF puede ocurrir si se cierra la entrada estándar; se controla sin traceback.
        raise SalidaSolicitada from exc


def registrar_error_entrada(error: Exception, campo: str) -> None:
    """Muestra y registra inmediatamente un error de validación de un campo."""
    registrar_error(error, f"Validación inmediata del campo '{campo}'", incluir_traza=error.__cause__ is not None)
    print(f"\n[ERROR] {error}")
    print("Por favor, corrija este mismo dato para poder continuar.\n")


def pedir_texto(mensaje: str, campo: str, minimo: int = 1, maximo: int = 100,
                validador: Optional[Callable[[str], None]] = None) -> str:
    """Solicita texto y repite el mismo campo hasta que supere todas las validaciones."""
    while True:
        valor = leer_entrada(mensaje)
        try:
            if not valor:
                raise ErrorValidacion(f"{campo.capitalize()} es obligatorio.")
            if not minimo <= len(valor) <= maximo:
                raise ErrorValidacion(f"{campo.capitalize()} debe tener entre {minimo} y {maximo} caracteres.")
            if validador:
                validador(valor)
            return valor
        except ErrorSistema as error:
            registrar_error_entrada(error, campo)


def pedir_entero(mensaje: str, campo: str, minimo: int, maximo: int) -> int:
    """Solicita un entero dentro de un rango y no avanza mientras sea inválido."""
    while True:
        valor = leer_entrada(mensaje)
        try:
            if not re.fullmatch(r"[+-]?\d+", valor):
                raise ErrorValidacion(f"{campo.capitalize()} debe ser un número entero.")
            numero = int(valor)
            if numero < minimo or numero > maximo:
                raise ErrorValidacion(f"{campo.capitalize()} debe estar entre {minimo} y {maximo}.")
            return numero
        except ErrorSistema as error:
            registrar_error_entrada(error, campo)


def pedir_decimal(mensaje: str, campo: str, minimo: Decimal,
                  maximo: Optional[Decimal] = None) -> Decimal:
    """Solicita un número decimal; acepta coma o punto como separador decimal."""
    while True:
        valor = leer_entrada(mensaje)
        try:
            if not valor:
                raise ErrorValidacion(f"{campo.capitalize()} es obligatorio.")
            # Se admite un único separador decimal y no se admiten separadores de miles.
            if valor.count(",") + valor.count(".") > 1:
                raise ErrorValidacion(f"{campo.capitalize()} debe usar un solo separador decimal.")
            numero = a_decimal(valor, campo)
            if numero < minimo:
                raise ErrorValidacion(f"{campo.capitalize()} no puede ser menor que {minimo}.")
            if maximo is not None and numero > maximo:
                raise ErrorValidacion(f"{campo.capitalize()} no puede superar {maximo}.")
            return numero
        except ErrorSistema as error:
            registrar_error_entrada(error, campo)


def pedir_opcion(mensaje: str, opciones: set[int]) -> int:
    """Solicita una opción de menú que pertenezca al conjunto permitido."""
    while True:
        valor = leer_entrada(mensaje)
        try:
            if not re.fullmatch(r"\d+", valor):
                raise ErrorValidacion("Debe ingresar el número de una opción válida.")
            opcion = int(valor)
            if opcion not in opciones:
                raise ErrorValidacion(f"La opción debe ser una de estas: {', '.join(map(str, sorted(opciones)))}.")
            return opcion
        except ErrorSistema as error:
            registrar_error_entrada(error, "opción de menú")


def validar_nombre(valor: str) -> None:
    """Valida que un nombre contenga letras y separadores habituales."""
    if not all(caracter.isalpha() or caracter in " .'-’" for caracter in valor):
        raise ErrorValidacion("El nombre solo puede contener letras, espacios, puntos o guiones.")
    if sum(caracter.isalpha() for caracter in valor) < 2:
        raise ErrorValidacion("El nombre debe contener al menos dos letras.")


def pedir_documento(sistema) -> str:
    """Solicita un documento con formato válido y que no esté registrado."""
    def validar(valor: str) -> None:
        # La expresión [0-9] permite únicamente los diez dígitos numéricos.
        # De esta manera se rechazan letras, espacios, guiones y símbolos inmediatamente.
        if not re.fullmatch(r"[0-9]{5,20}", valor):
            raise ErrorValidacion(
                "El documento debe contener únicamente números y tener entre 5 y 20 dígitos."
            )
        if any(cliente.documento == valor for cliente in sistema.clientes):
            raise ErrorValidacion("Ya existe un cliente registrado con ese documento.")
    return pedir_texto("Documento: ", "documento", 5, 20, validar)


def pedir_correo(sistema, correo_actual: Optional[str] = None) -> str:
    """Solicita un correo válido y evita duplicados entre clientes."""
    def validar(valor: str) -> None:
        if not re.fullmatch(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", valor):
            raise ErrorValidacion("Ingrese un correo válido, por ejemplo usuario@dominio.com.")
        if any(cliente.correo == valor.lower() and cliente.correo != correo_actual for cliente in sistema.clientes):
            raise ErrorValidacion("Ese correo ya está asociado a otro cliente.")
    return pedir_texto("Correo electrónico: ", "correo", 6, 120, validar)


def pedir_telefono() -> str:
    """Solicita un teléfono con caracteres permitidos y entre 7 y 15 dígitos."""
    def validar(valor: str) -> None:
        digitos = re.sub(r"\D", "", valor)
        if not re.fullmatch(r"\+?[0-9](?:[0-9() .-]*[0-9])", valor) or not 7 <= len(digitos) <= 15:
            raise ErrorValidacion("Ingrese un teléfono válido con entre 7 y 15 dígitos.")
    return pedir_texto("Teléfono: ", "teléfono", 7, 25, validar)


def pedir_fecha_hora_futura(validador_horario: Optional[Callable[[datetime], None]] = None) -> datetime:
    """Solicita fecha y hora futuras, validando cada campo antes de pasar al siguiente.

    El validador opcional permite comprobar choques de agenda al ingresar la hora,
    de modo que el usuario corrija ese mismo campo sin avanzar a otra operación.
    """
    while True:
        fecha_texto = pedir_texto("Fecha de la reserva (AAAA-MM-DD): ", "fecha", 10, 10)
        try:
            fecha_reserva = datetime.strptime(fecha_texto, "%Y-%m-%d").date()
            if fecha_reserva < date.today():
                raise ErrorValidacion("La fecha de la reserva no puede estar en el pasado.")
            break
        except ValueError as exc:
            error = ErrorValidacion("La fecha debe tener el formato AAAA-MM-DD y existir en el calendario.")
            error.__cause__ = exc
            registrar_error_entrada(error, "fecha")
        except ErrorSistema as error:
            registrar_error_entrada(error, "fecha")

    while True:
        hora_texto = pedir_texto("Hora de la reserva (HH:MM, formato 24 horas): ", "hora", 5, 5)
        try:
            hora_reserva = datetime.strptime(hora_texto, "%H:%M").time()
            momento = datetime.combine(fecha_reserva, hora_reserva)
            if momento <= datetime.now():
                raise ErrorValidacion("La fecha y hora de la reserva deben ser futuras.")
            if validador_horario:
                validador_horario(momento)
            return momento
        except ValueError as exc:
            error = ErrorValidacion("La hora debe tener el formato HH:MM entre 00:00 y 23:59.")
            error.__cause__ = exc
            registrar_error_entrada(error, "hora")
        except ErrorSistema as error:
            registrar_error_entrada(error, "hora")


# ---------------------------- SISTEMA PRINCIPAL ---------------------------

class SistemaGestion:
    """Administra las listas internas y coordina clientes, servicios y reservas."""

    def __init__(self):
        # Las listas se mantienen únicamente en memoria; no se usa una base de datos.
        self.clientes: list[Cliente] = []
        self.servicios: list[Servicio] = []
        self.reservas: list[Reserva] = []

    @staticmethod
    def generar_id(prefijo: str, coleccion: list) -> str:
        """Genera identificadores consecutivos según la cantidad de elementos existentes."""
        return f"{prefijo}{len(coleccion) + 1:03d}"

    def buscar_cliente(self, identificador: str) -> Cliente:
        """Busca un cliente por su código y genera una excepción si no existe."""
        for cliente in self.clientes:
            if cliente.identificador == identificador.upper():
                return cliente
        raise RecursoNoEncontrado(f"No existe un cliente con código {identificador.upper()}.")

    def buscar_servicio(self, identificador: str) -> Servicio:
        """Busca un servicio por su código."""
        for servicio in self.servicios:
            if servicio.identificador == identificador.upper():
                return servicio
        raise RecursoNoEncontrado(f"No existe un servicio con código {identificador.upper()}.")

    def buscar_reserva(self, identificador: str) -> Reserva:
        """Busca una reserva por su código."""
        for reserva in self.reservas:
            if reserva.identificador == identificador.upper():
                return reserva
        raise RecursoNoEncontrado(f"No existe una reserva con código {identificador.upper()}.")

    def verificar_horario(self, cliente: Cliente, servicio: Servicio,
                          fecha_hora: datetime, duracion: Decimal) -> None:
        """Evita que un cliente o un servicio tenga dos reservas activas superpuestas."""
        nuevo_inicio = fecha_hora
        nuevo_fin = fecha_hora + timedelta(hours=float(duracion))
        for existente in self.reservas:
            if existente.estado not in {"PENDIENTE", "CONFIRMADA"}:
                continue
            mismo_cliente = existente.cliente.identificador == cliente.identificador
            mismo_servicio = existente.servicio.identificador == servicio.identificador
            if not (mismo_cliente or mismo_servicio):
                continue
            inicio_existente = existente.fecha_hora
            fin_existente = inicio_existente + timedelta(hours=float(existente.duracion))
            # Dos intervalos se cruzan si cada uno comienza antes de que termine el otro.
            if nuevo_inicio < fin_existente and inicio_existente < nuevo_fin:
                if mismo_cliente:
                    raise ConflictoReserva("El cliente ya tiene otra reserva en ese horario.")
                raise ConflictoReserva("El servicio ya tiene otra reserva en ese horario.")

    def crear_reserva(self, cliente: Cliente, servicio: Servicio, duracion: Decimal,
                      fecha_hora: datetime, parametros: dict) -> Reserva:
        """Construye, valida y almacena una reserva pendiente."""
        if not cliente.activo:
            raise ErrorOperacion("No se puede reservar para un cliente inactivo.")
        if not servicio.activo:
            raise ServicioNoDisponible("El servicio seleccionado no está disponible.")
        servicio.validar_parametros(duracion, **parametros)
        self.verificar_horario(cliente, servicio, fecha_hora, duracion)
        codigo = self.generar_id("R", self.reservas)
        reserva = Reserva(codigo, cliente, servicio, duracion, fecha_hora, parametros)
        # Se valida que el cálculo estimado sea correcto antes de guardar la reserva.
        reserva.calcular_total()
        self.reservas.append(reserva)
        return reserva

    # -------------------------- OPERACIONES CLIENTES ----------------------

    def registrar_cliente(self) -> None:
        """Solicita y registra un cliente solo cuando todos sus datos son válidos."""
        print("\n--- REGISTRO DE CLIENTE ---")
        nombre = pedir_texto("Nombre completo: ", "nombre", 2, 80, validar_nombre)
        documento = pedir_documento(self)
        correo = pedir_correo(self)
        telefono = pedir_telefono()
        codigo = self.generar_id("C", self.clientes)
        cliente = Cliente(codigo, nombre, documento, correo, telefono)
        self.clientes.append(cliente)  # Se agrega al final, cuando todos los campos son correctos.
        print(f"\n[OK] Cliente registrado correctamente con código {codigo}.")

    def listar_clientes(self, solo_activos: bool = False) -> None:
        """Muestra los clientes registrados, con opción de filtrar los activos."""
        print("\n--- CLIENTES REGISTRADOS ---")
        elementos = [c for c in self.clientes if c.activo or not solo_activos]
        if not elementos:
            print("No hay clientes para mostrar.")
            return
        for cliente in elementos:
            print(cliente)

    def actualizar_cliente(self) -> None:
        """Permite actualizar el correo y teléfono sin reemplazar datos válidos por errores."""
        if not self.clientes:
            raise ErrorOperacion("No hay clientes registrados para actualizar.")
        self.listar_clientes()
        codigo = pedir_texto(
            "Código del cliente: ", "código de cliente", 4, 10,
            lambda valor: self.buscar_cliente(valor.upper()),
        ).upper()
        cliente = self.buscar_cliente(codigo)
        correo = pedir_correo(self, correo_actual=cliente.correo)
        telefono = pedir_telefono()
        cliente.actualizar_contacto(correo, telefono)
        print("[OK] Los datos de contacto se actualizaron correctamente.")

    def cambiar_estado_cliente(self) -> None:
        """Activa o desactiva un cliente seleccionado."""
        if not self.clientes:
            raise ErrorOperacion("No hay clientes registrados.")
        self.listar_clientes()
        codigo = pedir_texto(
            "Código del cliente: ", "código de cliente", 4, 10,
            lambda valor: self.buscar_cliente(valor.upper()),
        ).upper()
        cliente = self.buscar_cliente(codigo)
        nuevo_estado = cliente.cambiar_estado()
        print(f"[OK] Cliente {cliente.identificador}: {'ACTIVO' if nuevo_estado else 'INACTIVO'}.")

    # -------------------------- OPERACIONES SERVICIOS ---------------------

    def registrar_servicio(self) -> None:
        """Crea una instancia de la clase derivada elegida por el usuario."""
        print("\n--- REGISTRO DE SERVICIO ---")
        print("1. Consultoría")
        print("2. Mantenimiento")
        print("3. Capacitación")
        tipo = pedir_opcion("Seleccione el tipo de servicio: ", {1, 2, 3})
        nombre = pedir_texto("Nombre del servicio: ", "nombre del servicio", 3, 80)
        tarifa = pedir_decimal("Tarifa (valor por hora): $", "tarifa", Decimal("0.01"), Decimal("1000000000"))
        codigo = self.generar_id("S", self.servicios)

        # La selección determina qué clase hija se construye: esto aplica herencia y polimorfismo.
        if tipo == 1:
            servicio = ServicioConsultoria(codigo, nombre, tarifa)
        elif tipo == 2:
            servicio = ServicioMantenimiento(codigo, nombre, tarifa)
        else:
            servicio = ServicioCapacitacion(codigo, nombre, tarifa)

        self.servicios.append(servicio)
        print(f"\n[OK] Servicio creado con código {codigo}.")
        print(servicio.descripcion())

    def listar_servicios(self, solo_disponibles: bool = False) -> None:
        """Recorre servicios de diferentes clases y llama sus métodos polimórficos."""
        print("\n--- SERVICIOS REGISTRADOS ---")
        elementos = [s for s in self.servicios if s.activo or not solo_disponibles]
        if not elementos:
            print("No hay servicios para mostrar.")
            return
        for servicio in elementos:
            print(servicio)
            print(f"   {servicio.descripcion()}")

    def cambiar_disponibilidad_servicio(self) -> None:
        """Permite marcar un servicio como disponible o no disponible."""
        if not self.servicios:
            raise ErrorOperacion("No hay servicios registrados.")
        self.listar_servicios()
        codigo = pedir_texto(
            "Código del servicio: ", "código de servicio", 4, 10,
            lambda valor: self.buscar_servicio(valor.upper()),
        ).upper()
        servicio = self.buscar_servicio(codigo)
        nuevo_estado = servicio.cambiar_estado()
        print(f"[OK] Servicio {servicio.identificador}: {'DISPONIBLE' if nuevo_estado else 'NO DISPONIBLE'}.")

    # -------------------------- OPERACIONES RESERVAS ----------------------

    def seleccionar_cliente_activo(self) -> Cliente:
        """Lista clientes activos y solicita un identificador válido."""
        self.listar_clientes(solo_activos=True)
        if not any(c.activo for c in self.clientes):
            raise ErrorOperacion("No existen clientes activos para realizar una reserva.")
        def validar_codigo(valor: str) -> None:
            cliente_encontrado = self.buscar_cliente(valor.upper())
            if not cliente_encontrado.activo:
                raise ErrorValidacion("El cliente seleccionado está inactivo.")

        codigo = pedir_texto(
            "Código del cliente: ", "código de cliente", 4, 10, validar_codigo
        ).upper()
        return self.buscar_cliente(codigo)

    def seleccionar_servicio_disponible(self) -> Servicio:
        """Lista servicios disponibles y solicita uno existente."""
        self.listar_servicios(solo_disponibles=True)
        if not any(s.activo for s in self.servicios):
            raise ServicioNoDisponible("No existen servicios disponibles para reservar.")
        def validar_codigo(valor: str) -> None:
            servicio_encontrado = self.buscar_servicio(valor.upper())
            if not servicio_encontrado.activo:
                raise ErrorValidacion("El servicio seleccionado no está disponible.")

        codigo = pedir_texto(
            "Código del servicio: ", "código de servicio", 4, 10, validar_codigo
        ).upper()
        return self.buscar_servicio(codigo)

    def pedir_parametros_servicio(self, servicio: Servicio) -> dict:
        """Solicita exclusivamente los parámetros que requiere el tipo de servicio."""
        if isinstance(servicio, ServicioConsultoria):
            print("Modalidad: 1. Virtual | 2. Presencial")
            opcion = pedir_opcion("Seleccione modalidad: ", {1, 2})
            return {"modalidad": "virtual" if opcion == 1 else "presencial"}
        if isinstance(servicio, ServicioMantenimiento):
            materiales = pedir_decimal(
                "Costo de materiales (puede ser 0): $", "costo de materiales",
                Decimal("0"), Decimal("1000000000"),
            )
            return {"materiales": materiales}
        if isinstance(servicio, ServicioCapacitacion):
            participantes = pedir_entero("Cantidad de participantes (1-30): ", "participantes", 1, 30)
            return {"participantes": participantes}
        # Esta rama protege el sistema si se agrega una nueva clase de servicio sin definir sus datos.
        raise ErrorValidacion("El tipo de servicio no tiene parámetros de reserva configurados.")

    def reservar_servicio(self) -> None:
        """Guía al usuario para crear una reserva pendiente con datos completos."""
        print("\n--- CREAR RESERVA ---")
        if not self.clientes:
            raise ErrorOperacion("Primero debe registrar al menos un cliente.")
        if not self.servicios:
            raise ErrorOperacion("Primero debe registrar al menos un servicio.")
        cliente = self.seleccionar_cliente_activo()
        servicio = self.seleccionar_servicio_disponible()

        if isinstance(servicio, ServicioConsultoria):
            duracion = pedir_decimal("Duración en horas (0.25 a 12): ", "duración", Decimal("0.25"), Decimal("12"))
        elif isinstance(servicio, ServicioMantenimiento):
            duracion = pedir_decimal("Duración en horas (1 a 24): ", "duración", Decimal("1"), Decimal("24"))
        else:
            duracion = pedir_decimal("Duración en horas (1 a 8): ", "duración", Decimal("1"), Decimal("8"))

        parametros = self.pedir_parametros_servicio(servicio)
        # La disponibilidad horaria se comprueba mientras se captura la hora.
        def validar_horario(momento: datetime) -> None:
            self.verificar_horario(cliente, servicio, momento, duracion)

        fecha_hora = pedir_fecha_hora_futura(validar_horario)
        reserva = self.crear_reserva(cliente, servicio, duracion, fecha_hora, parametros)
        print(f"\n[OK] Reserva {reserva.identificador} creada en estado PENDIENTE.")
        print(f"Costo estimado sin impuestos ni descuentos: {formato_dinero(reserva.calcular_total())}")

    def listar_reservas(self) -> None:
        """Muestra todas las reservas y su estado actual."""
        print("\n--- RESERVAS REGISTRADAS ---")
        if not self.reservas:
            print("No hay reservas registradas.")
            return
        for reserva in self.reservas:
            print(reserva)

    def seleccionar_reserva(self) -> Reserva:
        """Solicita el código de una reserva existente."""
        if not self.reservas:
            raise ErrorOperacion("No hay reservas registradas.")
        self.listar_reservas()
        codigo = pedir_texto(
            "Código de la reserva: ", "código de reserva", 4, 10,
            lambda valor: self.buscar_reserva(valor.upper()),
        ).upper()
        return self.buscar_reserva(codigo)

    def confirmar_reserva(self) -> None:
        """Confirma una reserva pendiente."""
        reserva = self.seleccionar_reserva()
        reserva.confirmar()
        print(f"[OK] La reserva {reserva.identificador} quedó CONFIRMADA.")

    def cancelar_reserva(self) -> None:
        """Cancela una reserva pendiente o confirmada."""
        reserva = self.seleccionar_reserva()
        reserva.cancelar()
        print(f"[OK] La reserva {reserva.identificador} quedó CANCELADA.")

    def procesar_reserva(self) -> None:
        """Solicita impuesto y descuento opcionales y procesa una reserva confirmada."""
        reserva = self.seleccionar_reserva()
        impuesto = pedir_decimal("Impuesto porcentual (0 a 100): ", "impuesto", Decimal("0"), Decimal("100"))
        descuento = pedir_decimal("Descuento porcentual (0 a 100): ", "descuento", Decimal("0"), Decimal("100"))
        total = reserva.procesar(impuesto, descuento)
        print(f"\n[OK] Reserva {reserva.identificador} PROCESADA.")
        print(f"Total final: {formato_dinero(total)}")

    def calcular_costo_reserva(self) -> None:
        """Calcula un estimado sin cambiar el estado de la reserva."""
        reserva = self.seleccionar_reserva()
        impuesto = pedir_decimal("Impuesto porcentual (0 a 100): ", "impuesto", Decimal("0"), Decimal("100"))
        descuento = pedir_decimal("Descuento porcentual (0 a 100): ", "descuento", Decimal("0"), Decimal("100"))
        total = reserva.calcular_total(impuesto, descuento)
        print(f"Costo estimado con impuesto y descuento: {formato_dinero(total)}")
        print("La reserva conserva su estado actual; este cálculo no la procesa.")

    # ------------------------------- MENÚS --------------------------------

    @staticmethod
    def ejecutar_operacion(accion: Callable, descripcion: str) -> None:
        """Ejecuta una acción, captura fallos y garantiza continuar en el menú."""
        try:
            accion()
        except ErrorSistema as error:
            # Las excepciones propias se muestran al usuario y se registran una sola vez.
            registrar_error(error, descripcion)
            print(f"\n[ERROR] {error}")
        except Exception as error:
            # Un fallo inesperado queda en el log con traza para poder investigarlo.
            registrar_error(error, f"Error inesperado en {descripcion}", incluir_traza=True)
            print("\n[ERROR] Ocurrió un problema inesperado. El sistema seguirá funcionando.")
            print(f"Detalle: {error}")
        else:
            # La sección else se ejecuta únicamente si la operación terminó sin excepción.
            pass
        finally:
            # finally se ejecuta tanto si la operación tuvo éxito como si falló.
            print("\n" + "-" * 72)

    def menu_clientes(self) -> None:
        """Submenú para registrar, consultar y actualizar clientes."""
        while True:
            print("\n========== GESTIÓN DE CLIENTES ==========")
            print("1. Registrar cliente")
            print("2. Listar clientes")
            print("3. Actualizar correo y teléfono")
            print("4. Activar/desactivar cliente")
            print("0. Volver al menú principal")
            opcion = pedir_opcion("Seleccione una opción: ", {0, 1, 2, 3, 4})
            if opcion == 0:
                return
            acciones = {
                1: (self.registrar_cliente, "registro de cliente"),
                2: (self.listar_clientes, "listado de clientes"),
                3: (self.actualizar_cliente, "actualización de cliente"),
                4: (self.cambiar_estado_cliente, "cambio de estado de cliente"),
            }
            accion, descripcion = acciones[opcion]
            self.ejecutar_operacion(accion, descripcion)

    def menu_servicios(self) -> None:
        """Submenú para crear, listar y cambiar disponibilidad de servicios."""
        while True:
            print("\n========== GESTIÓN DE SERVICIOS ==========")
            print("1. Registrar servicio")
            print("2. Listar servicios")
            print("3. Activar/desactivar servicio")
            print("0. Volver al menú principal")
            opcion = pedir_opcion("Seleccione una opción: ", {0, 1, 2, 3})
            if opcion == 0:
                return
            acciones = {
                1: (self.registrar_servicio, "registro de servicio"),
                2: (self.listar_servicios, "listado de servicios"),
                3: (self.cambiar_disponibilidad_servicio, "cambio de disponibilidad de servicio"),
            }
            accion, descripcion = acciones[opcion]
            self.ejecutar_operacion(accion, descripcion)

    def menu_reservas(self) -> None:
        """Submenú para crear, consultar, confirmar, cancelar y procesar reservas."""
        while True:
            print("\n========== GESTIÓN DE RESERVAS ==========")
            print("1. Crear reserva")
            print("2. Listar reservas")
            print("3. Confirmar reserva")
            print("4. Cancelar reserva")
            print("5. Procesar reserva")
            print("6. Calcular costo con impuesto/descuento (sin procesar)")
            print("0. Volver al menú principal")
            opcion = pedir_opcion("Seleccione una opción: ", {0, 1, 2, 3, 4, 5, 6})
            if opcion == 0:
                return
            acciones = {
                1: (self.reservar_servicio, "creación de reserva"),
                2: (self.listar_reservas, "listado de reservas"),
                3: (self.confirmar_reserva, "confirmación de reserva"),
                4: (self.cancelar_reserva, "cancelación de reserva"),
                5: (self.procesar_reserva, "procesamiento de reserva"),
                6: (self.calcular_costo_reserva, "cálculo de reserva"),
            }
            accion, descripcion = acciones[opcion]
            self.ejecutar_operacion(accion, descripcion)

    def menu_principal(self) -> None:
        """Mantiene el programa activo hasta que el usuario seleccione salir."""
        print("=" * 72)
        print(" SISTEMA INTEGRAL DE GESTIÓN DE CLIENTES, SERVICIOS Y RESERVAS")
        print("=" * 72)
        print("La información se conserva en memoria durante esta ejecución.")
        print(f"Archivo de errores: {RUTA_LOG}")

        while True:
            print("\n================ MENÚ PRINCIPAL ================")
            print("1. Gestión de clientes")
            print("2. Gestión de servicios")
            print("3. Gestión de reservas")
            print("0. Salir")
            try:
                opcion = pedir_opcion("Seleccione una opción: ", {0, 1, 2, 3})
                if opcion == 0:
                    print("\nGracias por utilizar el sistema. Hasta pronto.")
                    break
                if opcion == 1:
                    self.menu_clientes()
                elif opcion == 2:
                    self.menu_servicios()
                elif opcion == 3:
                    self.menu_reservas()
            except SalidaSolicitada:
                print("\nSe recibió una señal de fin de entrada. Cerrando de forma controlada.")
                break
            except KeyboardInterrupt:
                print("\nInterrupción solicitada por el usuario. Cerrando de forma controlada.")
                break
            except Exception as error:
                registrar_error(error, "bucle del menú principal", incluir_traza=True)
                print("\n[ERROR] Se presentó un inconveniente en el menú. Puede intentarlo nuevamente.")


def main() -> None:
    """Punto de entrada del programa; no ejecuta pruebas ni operaciones de demostración."""
    sistema = SistemaGestion()
    try:
        sistema.menu_principal()
    except SalidaSolicitada:
        print("Programa finalizado de forma controlada.")
    except KeyboardInterrupt:
        print("\nPrograma interrumpido por el usuario.")
    except Exception as error:
        # Este último control evita que una excepción no prevista cierre sin dejar registro.
        registrar_error(error, "error no controlado en main", incluir_traza=True)
        print("Se produjo un error inesperado. Revise sistema_gestion.log.")
    finally:
        # Se cierra el manejador al terminar para liberar correctamente el archivo.
        for manejador in logger.handlers:
            manejador.flush()
            manejador.close()
        logger.handlers.clear()


# Este condicional permite importar las clases sin iniciar automáticamente la aplicación.
# El programa solo muestra el menú cuando se ejecuta directamente este archivo.
if __name__ == "__main__":
    main()
