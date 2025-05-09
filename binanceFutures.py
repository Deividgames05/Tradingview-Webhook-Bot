import json
import time
import ccxt
import random
import string

with open('config.json') as config_file:
    config = json.load(config_file)


if config['EXCHANGES']['binance-futures']['TESTNET']:
    exchange = ccxt.binance({
        'apiKey': config['EXCHANGES']['binance-futures']['API_KEY'],
        'secret': config['EXCHANGES']['binance-futures']['API_SECRET'],
        'options': {
            'defaultType': 'future',
        },
        'urls': {
            'api': {
                'public': 'https://testnet.binancefuture.com/fapi/v1',
                'private': 'https://testnet.binancefuture.com/fapi/v1',
            }, }
    })
    exchange.set_sandbox_mode(True)
else:
    exchange = ccxt.binance({
        'apiKey': config['EXCHANGES']['binance-futures']['API_KEY'],
        'secret': config['EXCHANGES']['binance-futures']['API_SECRET'],
        'options': {
            'defaultType': 'future',
        },
        'urls': {
            'api': {
                'public': 'https://fapi.binance.com/fapi/v1',
                'private': 'https://fapi.binance.com/fapi/v1',
            }, }
    })

class Bot:

    def __init__(self):
        pass

    def create_string(self):
        N = 7
        res = ''.join(random.choices(string.ascii_uppercase + string.digits, k=N))
        baseId = 'x-40PTWbMI'
        self.clientId = baseId + str(res)
        return

    def close_position(self, symbol):
        position = exchange.fetch_positions(symbol)[0]['info']['positionAmt']
        self.create_string()
        params = {
            "newClientOrderId": self.clientId,
            'reduceOnly': True
        }
        if float(position) > 0:
            print("Closing Long Position")
            exchange.create_order(symbol, 'Market', 'Sell', float(position), price=None, params=params)
        else:
            print("Closing Short Position")
            exchange.create_order(symbol, 'Market', 'Buy', -float(position), price=None, params=params)

    def run(self, data):
        acao = data.get("acao", "")
        symbol = data["symbol"]
        valor_usdt = float(data.get("valor_usdt", 0.5))
        price = float(exchange.fetch_ticker(symbol)['last'])

        try:
            market = exchange.market(symbol)
            leverage = market.get("limits", {}).get("leverage", {}).get("max", 50) or 50
        except:
            leverage = 50

        tamanho = round((valor_usdt * leverage) / price, 3)

        posicoes = exchange.fetch_positions([symbol])
        posicao = next((p for p in posicoes if p['info']['symbol'] == symbol), None)
        quantidade_aberta = float(posicao['info']['positionAmt']) if posicao else 0

        self.create_string()
        params = {
            "newClientOrderId": self.clientId,
            'reduceOnly': False
        }

        if acao == "comprar":
            print(f"🟢 Comprando {tamanho} de {symbol}")
            exchange.create_order(symbol, 'market', 'buy', tamanho, params=params)

        elif acao == "vender":
            print(f"🔴 Vendendo {tamanho} de {symbol}")
            exchange.create_order(symbol, 'market', 'sell', tamanho, params=params)

        elif acao == "parcial_compra" and quantidade_aberta > 0:
            parcial = round(quantidade_aberta * 0.95, 3)
            print(f"✅ Vendendo 95% da posição comprada de {symbol}")
            exchange.create_order(symbol, 'market', 'sell', parcial, params={**params, "reduceOnly": True})

        elif acao == "parcial_venda" and quantidade_aberta < 0:
            parcial = round(abs(quantidade_aberta) * 0.95, 3)
            print(f"✅ Comprando 95% da posição vendida de {symbol}")
            exchange.create_order(symbol, 'market', 'buy', parcial, params={**params, "reduceOnly": True})

        elif acao == "final_compra" and quantidade_aberta > 0:
            print(f"🏁 Fechando os 5% restantes da compra em {symbol}")
            exchange.create_order(symbol, 'market', 'sell', abs(quantidade_aberta), params={**params, "reduceOnly": True})

        elif acao == "final_venda" and quantidade_aberta < 0:
            print(f"🏁 Fechando os 5% restantes da venda em {symbol}")
            exchange.create_order(symbol, 'market', 'buy', abs(quantidade_aberta), params={**params, "reduceOnly": True})

        elif acao == "stop_compra" and quantidade_aberta > 0:
            print(f"🛑 Stopando posição comprada de {symbol}")
            exchange.create_order(symbol, 'market', 'sell', abs(quantidade_aberta), params={**params, "reduceOnly": True})

        elif acao == "stop_venda" and quantidade_aberta < 0:
            print(f"🛑 Stopando posição vendida de {symbol}")
            exchange.create_order(symbol, 'market', 'buy', abs(quantidade_aberta), params={**params, "reduceOnly": True})

        else:
            print(f"⚠️ Nenhuma ação realizada para {symbol}. Ação: {acao}, Quantidade aberta: {quantidade_aberta}")
