from datetime import datetime
from log_config import get_logger
import pandas as pd
from config import prefix_buy, prefix_sell, config

logger = get_logger(__name__)


def filter_another_operations_df(df):
    # Crear una máscara para excluir los tickers específicos
    mask_not_allowed_tickers = ~df['ticker'].isin(['MGCGO', 'AL30', 'MGCBO', 'TDA24'])

    # Crear una máscara para excluir el tipo 'DEPOSIT'
    mask_not_deposit_type = df['type'] != 'DEPOSIT'

    # Aplicar ambas máscaras para filtrar el DataFrame
    filtered_df = df[mask_not_allowed_tickers & mask_not_deposit_type]

    return filtered_df


def filter_only(transfers, ticker):
    """
    To debug and filter only one tickettransfers
    """
    return [transfer for transfer in transfers if transfer['ticker'] == ticker]


def convert_to_template_format(df):
    # Crear un nuevo DataFrame con las columnas requeridas

    # Crear registros de posiciones cerradas
    df = df.apply(crear_registro_posicion_df, axis=1)

    # Ordenar por la columna 'Fecha de Apertura'
    df = df.sort_values(by='Fecha de Apertura')

    df = clean_and_prepare_dataframe(df)

    # Convertir DataFrame a una lista de listas, incluyendo los encabezados
    data_list = [df.columns.tolist()] + df.values.tolist()

    return data_list


def separate_transfers_by_type_df(df):
    # Filtrar las compras
    buys = df[df['type'] == 'BUY']

    # Filtrar las ventas
    sells = df[df['type'] == 'SELL']

    # Filtrar el resto de tipos que no son ni compra ni venta
    restante = df[~df['type'].isin(['BUY', 'SELL'])]

    return buys, sells, restante


def format_number(val):
    """Convert numbers to a string with a fixed precision and replace '.' with ','."""
    if isinstance(val, float):
        return "{:.2f}".format(round(val, 2)).replace('.', ',')
    if isinstance(val, int):
        return str(val)
    return val


def get_now_str():
    now = datetime.now()
    return now.strftime("%d-%m-%Y")


def prepare_dates_for_insert(df):
    """
    Prepara las fechas en el DataFrame para la inserción.

    Args:
        df (pd.DataFrame): DataFrame con fechas a preparar.

    Returns:
        pd.DataFrame: DataFrame con fechas preparadas.
    """
    # Convertir todas las columnas de tipo datetime64 a string
    for col in df.columns:
        if pd.api.types.is_datetime64_any_dtype(df[col]):
            df[col] = df[col].dt.strftime('%d-%m-%Y')

    return df


def replace_nans_with_zero(df):
    """
    Reemplaza NaN en el DataFrame con 0.

    :param df: DataFrame de pandas que contiene los datos.
    :return: Nuevo DataFrame con los valores NaN reemplazados por 0.
    """
    return df.fillna(' ')


def clean_and_prepare_dataframe(df):
    """
    Realiza la limpieza y preparación de un DataFrame para asegurar que esté en el formato correcto para insertar.

    Args:
        df (pd.DataFrame): DataFrame a limpiar y preparar.

    Returns:
        pd.DataFrame: DataFrame limpio y preparado.
    """

    df = prepare_dates_for_insert(df)

    df = replace_nans_with_zero(df)

    return df


def filter_already_inserted(transfers_df, already_inserted_df):
    """
    Filtra las transferencias que ya han sido insertadas previamente para evitar duplicados.

    Args:
        transfers_df (pd.DataFrame): DataFrame de transferencias nuevas a evaluar.
        already_inserted_df (pd.DataFrame): DataFrame de transferencias que ya han sido insertadas en el sistema.

    Returns:
        pd.DataFrame: DataFrame de transferencias que aún no han sido insertadas.

    Esta función utiliza un merge para identificar las transferencias duplicadas basadas en cinco columnas clave.
    """

    # Comprobar el tipo de datos de transfers_df y already_inserted_df
    logger.debug("Tipo de dato de transfers_df: %s", type(transfers_df))
    logger.debug("Tipo de dato de already_inserted_df: %s", type(already_inserted_df))

    # Inspeccionar las columnas de transfers_df y already_inserted_df
    logger.debug("Columnas en transfers_df: %s", transfers_df.columns)
    logger.debug("Columnas en already_inserted_df: %s", already_inserted_df.columns)

    # Definir las columnas clave para la comparación
    key_columns = ['Estado', 'Ticker', 'Cantidad']

    # Verificar que las columnas clave existan en ambos DataFrames
    missing_columns_transfers = [col for col in key_columns if col not in transfers_df.columns]
    missing_columns_inserted = [col for col in key_columns if col not in already_inserted_df.columns]

    if missing_columns_transfers:
        logger.error("Columnas faltantes en transfers_df: %s", missing_columns_transfers)
        return pd.DataFrame()
    if missing_columns_inserted:
        logger.error("Columnas faltantes en already_inserted_df: %s", missing_columns_inserted)
        return pd.DataFrame()

    # Convertir las columnas clave a string para estandarización
    for col in key_columns:
        if col in transfers_df.columns:
            transfers_df[col] = transfers_df[col].astype(str)
        if col in already_inserted_df.columns:
            already_inserted_df[col] = already_inserted_df[col].astype(str)

    # Crear una clave única combinando las columnas clave
    transfers_df['unique_key'] = transfers_df[key_columns].apply(lambda row: '_'.join(row.values), axis=1)
    already_inserted_df['unique_key'] = already_inserted_df[key_columns].apply(lambda row: '_'.join(row.values), axis=1)

    # Realizar un merge para encontrar las transferencias no duplicadas
    filtered_transfers_df = transfers_df[~transfers_df['unique_key'].isin(already_inserted_df['unique_key'])]

    # Eliminar la columna de clave única antes de devolver el DataFrame
    filtered_transfers_df.drop(columns=['unique_key'], inplace=True)

    logger.info("Total de transferencias recibidas: %s", len(transfers_df))
    logger.info("Total de transferencias ya insertadas: %s", len(already_inserted_df))
    logger.info("Transferencias coincidentes filtradas: %s", len(transfers_df) - len(filtered_transfers_df))
    logger.info("Transferencias a insertar: %s", len(filtered_transfers_df))

    return filtered_transfers_df


def calcular_rentabilidad_ars(monto_ingreso, monto_egreso):
    # Calcular la rentabilidad en ARS
    return monto_egreso - monto_ingreso


def calcular_rentabilidad_porcentaje(monto_ingreso, rentabilidad_ars):
    # Calcular la rentabilidad en porcentaje
    return (rentabilidad_ars / monto_ingreso) * 100


def calcular_dias_entre_fechas(fecha_compra, fecha_venta):
    # Calcular la cantidad de días entre dos fechas
    fecha_compra = pd.to_datetime(fecha_compra)
    fecha_venta = pd.to_datetime(fecha_venta)
    return (fecha_venta - fecha_compra).days


def calcular_cagr(vi, vf, dias):
    """
    Calcula la tasa de retorno anualizada (CAGR) de una inversión.

    Args:
    vi (float): Valor inicial de la inversión.
    vf (float): Valor final de la inversión.
    dias (int): Número de días que la inversión estuvo abierta.

    Returns:
    float: Tasa de retorno anualizada.
    """
    n = dias / 365  # Convertir días a años
    cagr = (vf / vi) ** (1 / n) - 1
    return cagr


def crear_registro_posicion_df(row):
    try:
        monto_ingreso = abs(row[f"{prefix_buy}{config['monto']}"])
        monto_egreso = row[f"{prefix_sell}{config['monto']}"]

        ticker = row[f"{prefix_buy}{config['ticker']}"]
        fecha_apertura = row[f"{prefix_buy}{config['fecha']}"]
        cantidad = row[f"{prefix_buy}{config['cantidad']}"]
        precio_ingreso = abs(row[f"{prefix_buy}{config['precio']}"])
        fecha_cierre = row[f"{prefix_sell}{config['fecha']}"]
        observaciones = row.get('observacion', '')
        rentabilidad_ars = calcular_rentabilidad_ars(monto_ingreso, monto_egreso)

        # Van a depender de si la operación está abierta o cerrada
        dias = calcular_dias_entre_fechas(fecha_apertura, fecha_cierre)
        rentabilidad_ars_hoy = ''
        rentabilidad_a_hoy = ''

        # Obtener el precio hoy si existe, de lo contrario dejarlo vacío
        precio_hoy = row.get('buy_Precio Hoy', '')

        # if monto_egreso is nan, then the operation is still open
        estado = 'Abierta' if pd.isna(monto_egreso) or monto_egreso == '' else 'Cerrada'

        if estado == 'Abierta':
            dias = formula_dias()

            # Calcular rentabilidad a HOY
            if precio_hoy != '':
                rentabilidad_ars_hoy = (precio_hoy - precio_ingreso) * cantidad
                rentabilidad_a_hoy = calcular_rentabilidad_porcentaje(monto_ingreso, rentabilidad_ars_hoy)


        return pd.Series({
            'Estado': estado,
            'Ticker': ticker,
            'Fecha de Apertura': fecha_apertura,
            'Cantidad': cantidad,
            'Precio Ingreso': precio_ingreso,
            'Monto Ingreso': monto_ingreso,
            'Precio Hoy': precio_hoy,
            'Rentabilidad a HOY %': rentabilidad_a_hoy,
            'Rentabilidad ARs': rentabilidad_ars_hoy,
            'Fecha de Cierre': fecha_cierre,
            'Dias': dias,
            'Ars Cierre': monto_egreso,
            'Rentabilidad Ars': rentabilidad_ars,
            'Rentabilidad %': calcular_rentabilidad_porcentaje(monto_ingreso, rentabilidad_ars),
            'Observaciones': observaciones
        })

    except KeyError as e:
        print(f"Error: clave {e} no encontrada en el DataFrame")
        return pd.Series()

    except Exception as e:
        print(f"Error inesperado: {e}")
        return pd.Series()

def formula_dias():
    return '=DAYS(TODAY(); INDIRECT("C" & ROW()))'
