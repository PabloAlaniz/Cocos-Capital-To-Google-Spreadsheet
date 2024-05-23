import pandas as pd
from log_config import get_logger
from config import prefix_buy, prefix_sell, config
logger = get_logger(__name__)
pd.set_option('display.max_rows', None)

class TradingOperations:
    def __init__(self):
        # Configuración inicial con los nombres de las columnas con sufijos
        self.config = config
        self.prefix_buy = prefix_buy
        self.prefix_sell = prefix_sell

        # Variables para almacenar el estado de las transacciones
        self.posiciones_cerradas = pd.DataFrame()
        self.non_matched_buys = pd.DataFrame()
        self.non_matched_sells = pd.DataFrame()

    def analizar_match(self, buys_df, sells_df):
        # Realizar la coincidencia exacta de transacciones
        self._match_exacto(buys_df, sells_df)

        # Si hay transacciones no coincidentes, intentar una coincidencia acumulada
        if not self.non_matched_buys.empty and not self.non_matched_sells.empty:
            self._match_acumulado()
        else:
            logger.info("No hay transacciones no coincidentes para coincidencia acumulada.")

        if not self.non_matched_buys.empty or not self.non_matched_sells.empty:
            self._match_ventas_acumuladas()

        # Retornar las posiciones cerradas y las transacciones no coincidentes (por ende abiertas)
        return self.posiciones_cerradas, self.non_matched_buys, self.non_matched_sells

    def _match_exacto(self, buys_df, sells_df):

        # Inicializar DataFrame para coincidencias exactas
        matched_df = pd.DataFrame()
        # To do: matched_df lo puedo mover al init asi lo inicializo una sola vez. Pero usaria una linea igual para resetearlo?

        # Iterar sobre buys_df para encontrar matches exactos
        for buy_index, buy_row in buys_df.iterrows():
            sell_match = sells_df[
                (sells_df['quantity'] == -buy_row['quantity']) &
                (sells_df[self.config['ticker']] == buy_row[self.config['ticker']])
            ]
            if not sell_match.empty:
                sell_index = sell_match.index[0]
                # Agregar prefijos a las columnas para identificar compra y venta
                buy_row_prefixed = buy_row.add_prefix('buy_')
                sell_row_prefixed = sell_match.iloc[0].add_prefix('sell_')
                matched_row = pd.concat([buy_row_prefixed, sell_row_prefixed], axis=0).to_frame().T
                matched_df = pd.concat([matched_df, matched_row], ignore_index=True)

                # Eliminar las filas emparejadas
                sells_df = sells_df.drop(sell_index)
                buys_df = buys_df.drop(buy_index)

        # Log del DataFrame emparejado
        logger.info(f"Matched DataFrame: {matched_df}")

        # Añadir una observación para coincidencias exactas
        matched_df['observacion'] = "Match exacto."

        # Guarda las posiciones cerradas y las que no coincidieron
        self.posiciones_cerradas = matched_df
        self.non_matched_buys = buys_df
        self.non_matched_sells = sells_df

        self.log_unmatched_and_closed_positions()

    def _match_acumulado(self):

        #self.filter_transactions_for_debug(['CECO2', 'AGRO'])

        # Ordenar los DataFrames por fecha
        self.non_matched_buys = self.non_matched_buys.sort_values(by=self.config['fecha'])
        self.non_matched_sells = self.non_matched_sells.sort_values(by=self.config['fecha'])

        buys_to_drop = []  # Lista para almacenar índices de compras a eliminar
        matched_df = pd.DataFrame()
        accumulated_data = {}

        for buy_index, buy_row in self.non_matched_buys.iterrows():
            buy_ticker = buy_row.to_dict()['ticker']

            if buy_ticker not in accumulated_data:
                accumulated_data[buy_ticker] = {'quantity': 0, 'amount': 0, 'buys_used': []}
            accumulated_data[buy_ticker]['quantity'] += buy_row[self.config['cantidad']]
            accumulated_data[buy_ticker]['amount'] += buy_row[self.config['monto']]
            accumulated_data[buy_ticker]['buys_used'].append(buy_index)  # Añadir esta compra a la lista de usadas

            buy_quantity_accumulated = accumulated_data[buy_ticker]['quantity']
            buy_amount_accumulated = accumulated_data[buy_ticker]['amount']

            logger.debug(
                f"Acumulando compra: {buy_ticker} | cantidad: {buy_row.to_dict()['quantity']} | monto: {buy_row[self.config['monto']]} | buy_quantity_accumulated: {buy_quantity_accumulated} | buy_amount_accumulated: {buy_amount_accumulated}")

            matching_sells = self.non_matched_sells[self.non_matched_sells['ticker'] == buy_ticker].copy()

            sells_to_drop = []
            for sell_index, sell_row in matching_sells.iterrows():
                sell_quantity = abs(sell_row[self.config['cantidad']])

                if buy_quantity_accumulated == sell_quantity:
                    logger.debug(f"Match registrado. {buy_ticker} | {sell_quantity}")

                    matched_buy_amount = (sell_quantity / buy_quantity_accumulated) * buy_amount_accumulated

                    buy_row_prefixed = buy_row.add_prefix('buy_')
                    buy_row_prefixed['buy_' + self.config['cantidad']] = buy_quantity_accumulated
                    buy_row_prefixed['buy_' + self.config['monto']] = matched_buy_amount

                    sell_row_prefixed = sell_row.add_prefix('sell_')
                    matched_row = pd.concat([buy_row_prefixed, sell_row_prefixed], axis=0).to_frame().T

                    matched_df = pd.concat([matched_df, matched_row], ignore_index=True)

                    # Restablecer los acumulados después del match
                    accumulated_data[buy_ticker]['quantity'] = 0
                    accumulated_data[buy_ticker]['amount'] = 0

                    sells_to_drop.append(sell_index)

                    # Eliminamos todas las compras que se usaron para el match
                    buys_to_drop.extend(accumulated_data[buy_ticker]['buys_used'])

                    # Reiniciamos la lista de compras usadas para el próximo match
                    accumulated_data[buy_ticker]['buys_used'] = []

                    break

            # Eliminar ventas que hicieron match
            self.non_matched_sells = self.non_matched_sells.drop(sells_to_drop)

        # Eliminar compras que hicieron match después del bucle principal
        self.non_matched_buys = self.non_matched_buys.drop(buys_to_drop)

        matched_df['observacion'] = "Compras acumuladas."

        self.posiciones_cerradas = pd.concat([self.posiciones_cerradas, matched_df], ignore_index=True)

        self.log_unmatched_and_closed_positions()

    def _match_ventas_acumuladas(self):
        # Ordenar los DataFrames por fecha
        self.non_matched_buys = self.non_matched_buys.sort_values(by=self.config['fecha'])
        self.non_matched_sells = self.non_matched_sells.sort_values(by=self.config['fecha'])

        sells_to_drop = []  # Lista para almacenar índices de ventas a eliminar
        matched_df = pd.DataFrame()
        accumulated_data = {}

        for sell_index, sell_row in self.non_matched_sells.iterrows():
            sell_ticker = sell_row['ticker']

            if sell_ticker not in accumulated_data:
                accumulated_data[sell_ticker] = {'quantity': 0, 'amount': 0, 'indices': [], 'last_date': None}
            accumulated_data[sell_ticker]['quantity'] += abs(sell_row[self.config['cantidad']])
            accumulated_data[sell_ticker]['amount'] += sell_row[self.config['monto']]
            accumulated_data[sell_ticker]['indices'].append(sell_index)
            accumulated_data[sell_ticker]['last_date'] = sell_row[self.config['fecha']]

            sell_quantity_accumulated = accumulated_data[sell_ticker]['quantity']
            sell_amount_accumulated = accumulated_data[sell_ticker]['amount']

            logger.debug(
                f"Acumulando venta: {sell_ticker} | cantidad: {sell_row[self.config['cantidad']]} |"
                f"Cantidad Acumulada: {sell_quantity_accumulated} | Monto Acumulado: {sell_amount_accumulated}"
            )

            # Calcular el precio promedio ponderado por unidad de las ventas acumuladas
            average_price_per_unit = sell_amount_accumulated / sell_quantity_accumulated if sell_quantity_accumulated != 0 else 0

            # Filtrar las compras correspondientes al ticker actual
            matching_buys = self.non_matched_buys[self.non_matched_buys['ticker'] == sell_ticker].copy()

            buys_to_drop = []
            for buy_index, buy_row in matching_buys.iterrows():
                buy_quantity = buy_row[self.config['cantidad']]
                logger.info("Comparando compra con venta: %s | %s", buy_quantity, sell_quantity_accumulated)
                if sell_quantity_accumulated == buy_quantity:
                    logger.info(f"Match registrado. {sell_ticker} | {buy_quantity}")

                    matched_sell_amount = sell_quantity_accumulated * average_price_per_unit

                    sell_row_prefixed = buy_row.add_prefix('sell_')
                    sell_row_prefixed['sell_' + self.config['cantidad']] = sell_quantity_accumulated
                    sell_row_prefixed['sell_' + self.config['monto']] = matched_sell_amount
                    sell_row_prefixed['sell_' + self.config['fecha']] = accumulated_data[sell_ticker]['last_date']

                    buy_row_prefixed = buy_row.add_prefix('buy_')
                    matched_row = pd.concat([sell_row_prefixed, buy_row_prefixed], axis=0).to_frame().T

                    matched_df = pd.concat([matched_df, matched_row], ignore_index=True)

                    # Restablecer los acumulados después del match
                    accumulated_data[sell_ticker]['quantity'] = 0
                    accumulated_data[sell_ticker]['amount'] = 0

                    buys_to_drop.append(buy_index)

                    # Eliminamos todas las compras que se usaron para el match
                    sells_to_drop.extend(accumulated_data[sell_ticker]['indices'])

                    # Reiniciamos la lista de compras usadas para el próximo match
                    accumulated_data[sell_ticker]['indices'] = []

                    break

            # Eliminar compras que hicieron match después del bucle principal
            self.non_matched_buys = self.non_matched_buys.drop(buys_to_drop)

        # Eliminar ventas que hicieron match
        self.non_matched_sells = self.non_matched_sells.drop(sells_to_drop)

        matched_df['observacion'] = "Ventas acumuladas."

        self.posiciones_cerradas = pd.concat([self.posiciones_cerradas, matched_df], ignore_index=True)

    def filter_transactions_for_debug(self, tickers_to_debug):
        """Filtra las transacciones de compra y venta por tickers específicos para depuración."""
        self.non_matched_buys = self.non_matched_buys[
            self.non_matched_buys[self.config['ticker']].isin(tickers_to_debug)]
        self.non_matched_sells = self.non_matched_sells[
            self.non_matched_sells[self.config['ticker']].isin(tickers_to_debug)]

    def log_unmatched_and_closed_positions(self):
        """Registra en el log las compras y ventas no emparejadas, y las posiciones cerradas."""
        logger.info(f"Non matched buys: {self.non_matched_buys}")
        logger.info(f"Non matched sells: {self.non_matched_sells}")
        logger.info(f"Posiciones cerradas: {self.posiciones_cerradas}")


# Todo: Manejo de dividendos
# Todo: Manejo de splits
# Todo: Impuestos y comisiones