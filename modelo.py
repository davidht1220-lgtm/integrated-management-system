
"""
SISTEMA INTEGRAL DE GESTIÓN DE CLIENTES, SERVICIOS Y RESERVAS

Aplicación académica desarrollada en Python para ejecutarse por consola.
No utiliza bases de datos ni interfaces gráficas. La información se conserva
únicamente en listas mientras el programa está abierto. El archivo de logs se
utiliza exclusivamente para registrar errores reales detectados durante el uso.
"""

# ----------------------------- IMPORTACIONES -----------------------------

from abc import ABC, abstractmethod  # Permite crear clases y métodos abstractos.
from datetime import datetime, date, time, timedelta  # Manejo de fechas y horarios.
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP  # Cálculos monetarios precisos.
from pathlib import Path  # Permite construir rutas compatibles con Windows y otros sistemas.
import logging  # Registra los errores que realmente ocurren.
import re  # Permite validar formatos como correo, documento y teléfono.
import sys  # Permite consultar información del entorno de ejecución.
from typing import Callable, Optional  # Ayuda a documentar los tipos de datos.


# -------------------------- CONFIGURACIÓN DE LOGS -------------------------

# El archivo se crea en la misma carpeta que este programa.
RUTA_LOG = Path(__file__).resolve().with_name("sistema_gestion.log")

# Se configura un registrador que guarda únicamente errores y no muestra logs duplicados.
logger = logging.getLogger("SistemaGestion")

logger.setLevel(logging.ERROR)
logger.propagate = False

# Se agrega el manejador una sola vez para evitar duplicar mensajes si el módulo se importa.
if not logger.handlers:
    manejador = logging.FileHandler(RUTA_LOG, mode="a", encoding="utf-8")
    formato = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    manejador.setFormatter(formato)
    logger.addHandler(manejador)


def registrar_error(error: Exception, contexto: str, incluir_traza: bool = False) -> None:
    """Registra en el archivo de logs un error que ocurrió durante una operación real."""
    mensaje = f"{contexto} | {type(error).__name__}: {error}"
    # incluir_traza permite guardar también la traza cuando existe una excepción inesperada.
    logger.error(mensaje, exc_info=incluir_traza)


# -------------------------- EXCEPCIONES PROPIAS ---------------------------

class ErrorSistema(Exception):
    """Excepción base para los errores controlados de la aplicación."""


class ErrorValidacion(ErrorSistema):
    """Se genera cuando un dato ingresado no cumple las reglas establecidas."""


class ErrorOperacion(ErrorSistema):
    """Se utiliza cuando una acción no está permitida en el estado actual."""


class RecursoNoEncontrado(ErrorSistema):
    """Se genera cuando no existe un cliente, servicio o reserva solicitado."""


class ServicioNoDisponible(ErrorOperacion):
    """Se genera cuando se intenta reservar o confirmar un servicio inactivo."""


class EstadoReservaInvalido(ErrorOperacion):
    """Se genera cuando se intenta cambiar una reserva desde un estado no permitido."""


class ConflictoReserva(ErrorOperacion):
    """Se genera cuando el cliente o el servicio ya tiene una reserva en ese horario."""


class ErrorCalculo(ErrorSistema):
    """Se utiliza cuando un cálculo genera un resultado inconsistente."""


class SalidaSolicitada(Exception):
    """Excepción interna para cerrar de forma controlada ante Ctrl+Z o fin de entrada."""


# ---------------------------- CONSTANTES ---------------------------------

CENTAVO = Decimal("0.01")  # Precisión monetaria de dos decimales.
CERO = Decimal("0")


def a_decimal(valor, nombre: str = "valor") -> Decimal:
    """Convierte un dato a Decimal y conserva la causa del error si la conversión falla."""
    try:
        resultado = Decimal(str(valor).strip().replace(",", "."))
    except (InvalidOperation, ValueError, TypeError) as exc:
        # El encadenamiento conserva el error original para facilitar el diagnóstico.
        raise ErrorValidacion(f"El campo {nombre} debe contener un número válido.") from exc

    if not resultado.is_finite():
        raise ErrorValidacion(f"El campo {nombre} debe contener un número finito.")
    return resultado


def dinero(valor: Decimal) -> Decimal:
    """Redondea un valor monetario a dos decimales usando redondeo comercial."""
    resultado = valor.quantize(CENTAVO, rounding=ROUND_HALF_UP)
    if resultado < CERO:
        raise ErrorCalculo("El cálculo produjo un valor monetario negativo.")
    return resultado


def formato_dinero(valor: Decimal) -> str:
    """Muestra valores monetarios con separador de miles y dos decimales."""
    return f"${valor:,.2f}"


def validar_porcentaje(valor, nombre: str) -> Decimal:
    """Valida que un impuesto o descuento esté entre 0 y 100 por ciento."""
    porcentaje = a_decimal(valor, nombre)
    if porcentaje < CERO or porcentaje > Decimal("100"):
        raise ErrorValidacion(f"{nombre.capitalize()} debe estar entre 0 y 100.")
    return porcentaje


# --------------------------- CLASE ABSTRACTA ------------------------------

class Entidad(ABC):
    """Clase abstracta que reúne características comunes de las entidades del sistema."""

    def __init__(self, identificador: str):
        # El identificador se encapsula para impedir su modificación accidental.
        if not isinstance(identificador, str) or not identificador.strip():
            raise ErrorValidacion("El identificador de la entidad es obligatorio.")
        self.__identificador = identificador.strip().upper()
        self.__activo = True

    @property
    def identificador(self) -> str:
        """Entrega el identificador sin permitir modificarlo directamente."""
        return self.__identificador

    @property
    def activo(self) -> bool:
        """Indica si la entidad puede participar en nuevas operaciones."""
        return self.__activo

    def cambiar_estado(self) -> bool:
        """Activa o desactiva la entidad y devuelve su nuevo estado."""
        self.__activo = not self.__activo
        return self.__activo

    @abstractmethod
    def validar(self) -> None:
        """Obliga a las clases derivadas a implementar sus propias validaciones."""
        raise NotImplementedError


# ------------------------------- CLIENTE ----------------------------------

class Cliente(Entidad):
    """Representa a un cliente y mantiene sus datos personales encapsulados."""

    def __init__(self, identificador: str, nombre: str, documento: str,
                 correo: str, telefono: str):
        super().__init__(identificador)
        # Los atributos privados protegen la información del cliente.
        self.__nombre = nombre.strip()
        self.__documento = documento.strip()
        self.__correo = correo.strip().lower()
        self.__telefono = telefono.strip()
        self.validar()  # El objeto no se crea si alguno de sus datos es inválido.

    @property
    def nombre(self) -> str:
        return self.__nombre

    @property
    def documento(self) -> str:
        return self.__documento

    @property
    def correo(self) -> str:
        return self.__correo

    @property
    def telefono(self) -> str:
        return self.__telefono

    def validar(self) -> None:
        """Verifica la integridad de los datos personales del cliente."""
        if len(self.__nombre) < 2 or len(self.__nombre) > 80:
            raise ErrorValidacion("El nombre debe tener entre 2 y 80 caracteres.")
        if not all(caracter.isalpha() or caracter in " .'-’" for caracter in self.__nombre):
            raise ErrorValidacion("El nombre solo puede contener letras, espacios, puntos o guiones.")
        # El documento de identidad debe contener exclusivamente dígitos del 0 al 9.
        # Se exige una longitud de entre 5 y 20 dígitos y no se permiten letras,
        # espacios, guiones, puntos ni otros caracteres especiales.
        if not re.fullmatch(r"[0-9]{5,20}", self.__documento):
            raise ErrorValidacion("El documento debe contener únicamente números y tener entre 5 y 20 dígitos.")
        if not re.fullmatch(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", self.__correo):
            raise ErrorValidacion("El correo electrónico no tiene un formato válido.")
        digitos = re.sub(r"\D", "", self.__telefono)
        if not 7 <= len(digitos) <= 15:
            raise ErrorValidacion("El teléfono debe contener entre 7 y 15 dígitos.")
        if not re.fullmatch(r"\+?[0-9](?:[0-9() .-]*[0-9])", self.__telefono):
            raise ErrorValidacion("El teléfono debe iniciar con un dígito (o +) y finalizar con un dígito.")

    def actualizar_contacto(self, correo: str, telefono: str) -> None:
        """Actualiza correo y teléfono; si la validación falla, conserva los datos anteriores."""
        correo_anterior = self.__correo
        telefono_anterior = self.__telefono
        self.__correo = correo.strip().lower()
        self.__telefono = telefono.strip()
        try:
            self.validar()
        except ErrorValidacion:
            self.__correo = correo_anterior
            self.__telefono = telefono_anterior
            raise

    def __str__(self) -> str:
        return (f"{self.identificador} | {self.nombre} | Doc: {self.documento} | "
                f"Correo: {self.correo} | Teléfono: {self.telefono} | "
                f"Estado: {'Activo' if self.activo else 'Inactivo'}")


# --------------------------- CLASE ABSTRACTA SERVICIO ---------------------

class Servicio(Entidad, ABC):
    """Clase abstracta que define la estructura común de todos los servicios."""

    def __init__(self, identificador: str, nombre: str, tarifa: Decimal):
        super().__init__(identificador)
        self._nombre = nombre.strip()
        self._tarifa = a_decimal(tarifa, "tarifa")
        self.validar()

    @property
    def nombre(self) -> str:
        return self._nombre

    @property
    def tarifa(self) -> Decimal:
        return self._tarifa

    def validar(self) -> None:
        """Valida los datos que comparten todos los servicios."""
        if not 3 <= len(self._nombre) <= 80:
            raise ErrorValidacion("El nombre del servicio debe tener entre 3 y 80 caracteres.")
        if self._tarifa <= CERO or self._tarifa > Decimal("1000000000"):
            raise ErrorValidacion("La tarifa debe ser mayor que cero y no superar 1.000.000.000.")

    @staticmethod
    def validar_duracion(duracion, minimo: str, maximo: str) -> Decimal:
        """Valida la duración según los límites establecidos por cada servicio."""
        horas = a_decimal(duracion, "duración")
        if horas < Decimal(minimo) or horas > Decimal(maximo):
            raise ErrorValidacion(f"La duración debe estar entre {minimo} y {maximo} horas.")
        return horas

    def _aplicar_impuesto_y_descuento(self, costo_base: Decimal,
                                      impuesto=0, descuento=0) -> Decimal:
        """Aplica primero el descuento y luego el impuesto al costo base."""
        impuesto_validado = validar_porcentaje(impuesto, "impuesto")
        descuento_validado = validar_porcentaje(descuento, "descuento")
        if costo_base < CERO:
            raise ErrorCalculo("El costo base no puede ser negativo.")
        costo_con_descuento = costo_base * (Decimal("1") - descuento_validado / Decimal("100"))
        costo_con_impuesto = costo_con_descuento * (Decimal("1") + impuesto_validado / Decimal("100"))
        return dinero(costo_con_impuesto)

    @abstractmethod
    def descripcion(self) -> str:
        """Devuelve la descripción particular del servicio."""
        raise NotImplementedError

    @abstractmethod
    def validar_parametros(self, duracion, **parametros) -> dict:
        """Valida los parámetros adicionales exigidos por el tipo de servicio."""
        raise NotImplementedError

    @abstractmethod
    def calcular_costo(self, duracion, impuesto=0, descuento=0, **parametros) -> Decimal:
        """Calcula el costo con parámetros opcionales para simular sobrecarga."""
        raise NotImplementedError

    def __str__(self) -> str:
        estado = "Disponible" if self.activo else "No disponible"
        return f"{self.identificador} | {self.nombre} | Tarifa: {formato_dinero(self.tarifa)} | {estado}"


# ----------------------------- SERVICIOS DERIVADOS ------------------------

class ServicioConsultoria(Servicio):
    """Servicio cobrado por hora, con modalidad virtual o presencial."""

    def descripcion(self) -> str:
        return (f"Consultoría: acompañamiento profesional por hora. "
                f"Tarifa: {formato_dinero(self.tarifa)} por hora. "
                "La modalidad presencial tiene un recargo del 10%.")

    def validar_parametros(self, duracion, **parametros) -> dict:
        """Valida la duración y la modalidad de la consultoría."""
        horas = self.validar_duracion(duracion, "0.25", "12")
        modalidad = str(parametros.get("modalidad", "")).strip().lower()
        if modalidad not in {"virtual", "presencial"}:
            raise ErrorValidacion("La modalidad debe ser 'virtual' o 'presencial'.")
        if set(parametros) != {"modalidad"}:
            raise ErrorValidacion("La consultoría solo admite el parámetro modalidad.")
        return {"duracion": horas, "modalidad": modalidad}

    def calcular_costo(self, duracion, impuesto=0, descuento=0, **parametros) -> Decimal:
        """Calcula la consultoría; impuesto y descuento son opcionales."""
        datos = self.validar_parametros(duracion, **parametros)
        costo_base = self.tarifa * datos["duracion"]
        if datos["modalidad"] == "presencial":
            costo_base *= Decimal("1.10")
        return self._aplicar_impuesto_y_descuento(costo_base, impuesto, descuento)


class ServicioMantenimiento(Servicio):
    """Servicio de mantenimiento cobrado por hora más el costo de materiales."""

    def descripcion(self) -> str:
        return (f"Mantenimiento: diagnóstico y mantenimiento técnico por hora. "
                f"Tarifa: {formato_dinero(self.tarifa)} por hora, más materiales.")

    def validar_parametros(self, duracion, **parametros) -> dict:
        """Valida duración y costo de los materiales utilizados."""
        horas = self.validar_duracion(duracion, "1", "24")
        if set(parametros) != {"materiales"}:
            raise ErrorValidacion("El mantenimiento requiere únicamente el parámetro materiales.")
        materiales = a_decimal(parametros.get("materiales"), "costo de materiales")
        if materiales < CERO or materiales > Decimal("1000000000"):
            raise ErrorValidacion("El costo de materiales debe estar entre 0 y 1.000.000.000.")
        return {"duracion": horas, "materiales": materiales}

    def calcular_costo(self, duracion, impuesto=0, descuento=0, **parametros) -> Decimal:
        """Calcula horas de mantenimiento más materiales y aplica opcionalmente descuentos/impuestos."""
        datos = self.validar_parametros(duracion, **parametros)
        costo_base = self.tarifa * datos["duracion"] + datos["materiales"]
        return self._aplicar_impuesto_y_descuento(costo_base, impuesto, descuento)


class ServicioCapacitacion(Servicio):
    """Servicio de capacitación cuyo costo depende de las horas y participantes."""

    def descripcion(self) -> str:
        return (f"Capacitación: formación por hora y por participante. "
                f"Tarifa: {formato_dinero(self.tarifa)} por hora y participante. "
                "Admite grupos de 1 a 30 personas.")

    def validar_parametros(self, duracion, **parametros) -> dict:
        """Valida la duración de la capacitación y el número de participantes."""
        horas = self.validar_duracion(duracion, "1", "8")
        if set(parametros) != {"participantes"}:
            raise ErrorValidacion("La capacitación requiere únicamente el parámetro participantes.")
        participantes = parametros.get("participantes")
        if isinstance(participantes, bool) or not str(participantes).isdigit():
            raise ErrorValidacion("El número de participantes debe ser un entero.")
        cantidad = int(participantes)
        if not 1 <= cantidad <= 30:
            raise ErrorValidacion("La capacitación admite entre 1 y 30 participantes.")
        return {"duracion": horas, "participantes": cantidad}

    def calcular_costo(self, duracion, impuesto=0, descuento=0, **parametros) -> Decimal:
        """Calcula el valor por hora multiplicado por la cantidad de participantes."""
        datos = self.validar_parametros(duracion, **parametros)
        costo_base = self.tarifa * datos["duracion"] * datos["participantes"]
        return self._aplicar_impuesto_y_descuento(costo_base, impuesto, descuento)


# -------------------------------- RESERVA ---------------------------------

class Reserva(Entidad):
    """Relaciona un cliente con un servicio, fecha, duración y estado de reserva."""

    ESTADOS_VALIDOS = {"PENDIENTE", "CONFIRMADA", "CANCELADA", "PROCESADA"}

    def __init__(self, identificador: str, cliente: Cliente, servicio: Servicio,
                 duracion: Decimal, fecha_hora: datetime, parametros: dict):
        super().__init__(identificador)
        self.__cliente = cliente
        self.__servicio = servicio
        self.__duracion = a_decimal(duracion, "duración")
        self.__fecha_hora = fecha_hora
        # Se almacena una copia para evitar que otro objeto modifique los parámetros.
        self.__parametros = dict(parametros)
        self.__estado = "PENDIENTE"
        self.__costo_final: Optional[Decimal] = None
        self.validar()

    @property
    def cliente(self) -> Cliente:
        return self.__cliente

    @property
    def servicio(self) -> Servicio:
        return self.__servicio

    @property
    def duracion(self) -> Decimal:
        return self.__duracion

    @property
    def fecha_hora(self) -> datetime:
        return self.__fecha_hora

    @property
    def parametros(self) -> dict:
        # Se devuelve una copia para preservar la encapsulación.
        return dict(self.__parametros)

    @property
    def estado(self) -> str:
        return self.__estado

    @property
    def costo_final(self) -> Optional[Decimal]:
        return self.__costo_final

    def validar(self) -> None:
        """Comprueba que la reserva tenga relaciones y datos válidos."""
        if not isinstance(self.__cliente, Cliente):
            raise ErrorValidacion("La reserva debe estar asociada a un cliente válido.")
        if not isinstance(self.__servicio, Servicio):
            raise ErrorValidacion("La reserva debe estar asociada a un servicio válido.")
        if not isinstance(self.__fecha_hora, datetime):
            raise ErrorValidacion("La fecha y hora de la reserva no son válidas.")
        if self.__fecha_hora <= datetime.now():
            raise ErrorValidacion("La fecha y hora de la reserva deben ser futuras.")
        if self.__duracion <= CERO:
            raise ErrorValidacion("La duración de la reserva debe ser mayor que cero.")
        self.__servicio.validar_parametros(self.__duracion, **self.__parametros)

    def calcular_total(self, impuesto=0, descuento=0) -> Decimal:
        """Calcula el total con cero, uno o dos porcentajes opcionales.

        Ejemplos de uso: calcular_total(), calcular_total(19) o
        calcular_total(19, 10). Esta es la forma compatible con Python de
        ofrecer variantes de un método sin sobrecarga tradicional por firma.
        """
        return self.__servicio.calcular_costo(
            self.__duracion,
            impuesto=impuesto,
            descuento=descuento,
            **self.__parametros,
        )

    def confirmar(self) -> None:
        """Confirma una reserva pendiente si el cliente y el servicio están activos."""
        if self.__estado != "PENDIENTE":
            raise EstadoReservaInvalido("Solo se pueden confirmar reservas pendientes.")
        if not self.__cliente.activo:
            raise ErrorOperacion("No se puede confirmar: el cliente está inactivo.")
        if not self.__servicio.activo:
            raise ServicioNoDisponible("No se puede confirmar: el servicio está no disponible.")
        self.__estado = "CONFIRMADA"

    def cancelar(self) -> None:
        """Cancela una reserva pendiente o confirmada."""
        if self.__estado not in {"PENDIENTE", "CONFIRMADA"}:
            raise EstadoReservaInvalido("Solo se pueden cancelar reservas pendientes o confirmadas.")
        self.__estado = "CANCELADA"

    def procesar(self, impuesto=0, descuento=0) -> Decimal:
        """Procesa una reserva confirmada y guarda el costo final calculado."""
        if self.__estado != "CONFIRMADA":
            raise EstadoReservaInvalido("Solo se pueden procesar reservas confirmadas.")
        if not self.__servicio.activo:
            raise ServicioNoDisponible("No se puede procesar: el servicio está no disponible.")
        # El estado solo cambia después de que el cálculo haya finalizado correctamente.
        total = self.calcular_total(impuesto, descuento)
        if total < CERO:
            raise ErrorCalculo("El total de la reserva no puede ser negativo.")
        self.__costo_final = total
        self.__estado = "PROCESADA"
        return total

    def __str__(self) -> str:
        total = formato_dinero(self.__costo_final) if self.__costo_final is not None else "Pendiente de procesamiento"
        return (
            f"{self.identificador} | Cliente: {self.__cliente.nombre} ({self.__cliente.identificador}) | "
            f"Servicio: {self.__servicio.nombre} ({self.__servicio.identificador}) | "
            f"Fecha: {self.__fecha_hora.strftime('%Y-%m-%d %H:%M')} | "
            f"Duración: {self.__duracion} h | Estado: {self.__estado} | Total: {total}"
        )

