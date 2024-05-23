import transform_data
from config import USER, PASS, GOOGLE_SHEET_FILE, SHEET_TAB, JSONGOOGLEFILE, prefix_buy
from cocos import CocosCapital
from gspreadmanager import GoogleSheetConector
from transform_data import filter_already_inserted, filter_another_operations_df, separate_transfers_by_type_df, get_now_str, prepare_dates_for_insert
from log_config import get_logger
from trading_operations import TradingOperations
import pandas as pd
logger = get_logger(__name__)


class Trading:
    def __init__(self):
        self.cocos = CocosCapital(USER, PASS)
        self.sheet_connector = GoogleSheetConector(GOOGLE_SHEET_FILE, JSONGOOGLEFILE, SHEET_TAB)

    def insert_data(self, data, tab_name=SHEET_TAB):
        if len(data) > 0:
            logger.info("insert_data Insertando %s operaciones", len(data))
            self.sheet_connector.spreadsheet_append(data, tab_name)
        else:
            logger.info("No hay datos para insertar. Largo Data: %s", len(data))

    def get_and_filter_transfers(self, since, to=None):

        # Obtengo las transferencias (compras y ventas) de la API
        transfers = self.cocos.get_transfers(since, to)
        logger.info("Main.py Transferencias obtenidas: %s", len(transfers))

        # Convertir la lista de diccionarios a DataFrame
        transfers = pd.DataFrame(transfers)

        # Filtro las operaciones que no son ni compra ni venta.
        transfers = filter_another_operations_df(transfers)


        # Separar las transferencias por tipo
        buys_df, sells_df, restante_df = separate_transfers_by_type_df(transfers)

        # Usar len() para contar el número de filas en cada DataFrame
        logger.info("Main.py Compras: %s | Ventas: %s | Restante: %s", len(buys_df), len(sells_df), len(restante_df))

        return buys_df, sells_df, restante_df

    def get_and_save_range_movements(self, since, to=None):

        buys_df, sells_df, restante_df = self.get_and_filter_transfers(since, to)

        data = self.procesar_operaciones(buys_df, sells_df, restante_df)

        # Convierte la data al formato del template de la planilla
        data = transform_data.convert_to_template_format(data)

        # Filtro para dejar solo operaciones aun no insertadas.
        data = self.filter_new_operations(data)

        # Insertar
        self.insert_data(data)

    def procesar_operaciones(self, buys_df, sells_df, restante_df):

        operaciones = TradingOperations()
        operaciones_cerradas, remaining_buys, remaining_sells = operaciones.analizar_match(buys_df, sells_df)

        # No deberia quedar reimaining_sells. Si hay remainings_buys son operaciones abiertas.
        operaciones_abiertas = self.procesar_operaciones_abiertas(remaining_buys)

        data = pd.concat([operaciones_cerradas, operaciones_abiertas])

        return data

    def filter_new_operations(self, data):
        # Filtro las operaciones que ya fueron insertadas en el spreadsheet
        already_inserted = self.sheet_connector.read_sheet_data(tab_name=SHEET_TAB, output_format='pandas')

        # Comprobar si hay datos ya insertados
        if len(already_inserted) > 0:
            data = filter_already_inserted(data, already_inserted)
        else:
            logger.info("No hay datos previamente insertados.")

        return data

    def procesar_operaciones_abiertas(self, remaining_buys):

        # Obtener el precio de las operaciones abiertas
        remaining_buys = self.get_price_for_open_operations(remaining_buys)

        # Agregar el prefijo a todas las columnas del DataFrame
        remaining_buys = remaining_buys.add_prefix(prefix_buy)

        return remaining_buys

    def get_price_for_open_operations(self, remaining_buys):
        # Definir una función lambda que obtenga el precio usando el servicio de precios
        get_price = lambda ticker: self.get_price_for_ticker(ticker)

        # Aplicar la función a la columna 'ticker' para obtener los precios
        remaining_buys['Precio Hoy'] = remaining_buys['ticker'].apply(get_price)

        return remaining_buys

    def get_price_for_ticker(self, ticker, term="48hs"):
        price_data = self.cocos.get_ticket_price(ticker)
        if price_data:
            price = next((subtipo['last'] for subtipo in price_data if
                          subtipo['short_ticker'] == ticker and subtipo['term'] == term), None)
            return price
        return None

    def insert_total_daily(self):
        """
        Inserta los totales diarios de la cuenta en una hoja de cálculo de Google Sheets.

        Esta función recupera el total actual de la cuenta en ARS y USD, formatea la fecha actual
        y los montos numéricos para asegurarse de que se inserten correctamente en Google Sheets,
        y registra cada paso del proceso para facilitar la depuración. En caso de errores durante
        la inserción, estos se registran con detalles completos para diagnóstico.

        Args:
            self: Referencia a la instancia actual de la clase.

        Raises:
            Exception: Captura cualquier excepción que ocurra durante la recuperación de los totales,
                       el formateo de datos o la inserción en Google Sheets, y registra el error.

        Returns:
            None: La función no devuelve ningún valor, pero inserta los datos en Google Sheets.
        """
        try:
            # Obtiene el total de la cuenta desde el objeto `cocos`
            total = self.cocos.get_account_total()

            # Obtiene la fecha y hora actual en formato de cadena
            now_str = get_now_str()

            # Registra en el log los datos antes de insertarlos
            logger.debug(f"Fecha: {now_str}, Total ARS: {total['ars']}, Total USD: {total['usd']}")

            # Formatea los números para reducir la precisión a dos decimales
            ars_formatted = round(total['ars'], 2)
            usd_formatted = round(total['usd'], 2)

            # Prepara los datos para ser insertados en una lista de listas
            to_insert = [[now_str, ars_formatted, usd_formatted]]

            # Registra en el log los datos formateados que se van a insertar
            logger.debug(f"Datos preparados para insertar: {to_insert}")

            # Añade los datos formateados a la hoja de cálculo en Google Sheets
            self.sheet_connector.spreadsheet_append(to_insert, 'Total diario')

        except Exception as e:
            # Registra un mensaje de error en caso de fallar la inserción de datos
            logger.error("Error al insertar datos en Google Sheets", exc_info=True)