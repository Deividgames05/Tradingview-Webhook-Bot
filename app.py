import json
from flask import Flask, render_template, request, jsonify
from pybit import HTTP
import time
import ccxt
from binanceFutures import Bot

def validate_bybit_api_key(session):
    try:
        result = session.get_api_key_info()
        return True
    except Exception as e:
        print("Bybit API key validation failed:", str(e))
        return False

def validate_binance_api_key(exchange):
    try:
        result = exchange.fetch_balance()
        return True
    except Exception as e:
        print("Binance API key validation failed:", str(e))
        return False

app = Flask(__name__)

# load config.json
with open('config.json') as config_file:
    config = json.load(config_file)

###############################################################################
#
#             This Section is for Exchange Validation
#
###############################################################################

use_bybit = False
if 'BYBIT' in config['EXCHANGES']:
    if config['EXCHANGES']['BYBIT']['ENABLED']:
        print("Bybit is enabled!")
        use_bybit = True

    session = HTTP(
        endpoint='https://api.bybit.com',
        api_key=config['EXCHANGES']['BYBIT']['API_KEY'],
        api_secret=config['EXCHANGES']['BYBIT']['API_SECRET']
    )

use_binance_futures = False
if 'BINANCE-FUTURES' in config['EXCHANGES']:
    if config['EXCHANGES']['BINANCE-FUTURES']['ENABLED']:
        print("Binance is enabled!")
        use_binance_futures = True

        exchange = ccxt.binance({
        'apiKey': config['EXCHANGES']['BINANCE-FUTURES']['API_KEY'],
        'secret': config['EXCHANGES']['BINANCE-FUTURES']['API_SECRET'],
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

# Validate Bybit API key
if use_bybit:
    if not validate_bybit_api_key(session):
        print("Invalid Bybit API key.")
        use_bybit = False

# Validate Binance Futures API key
if use_binance_futures:
    if not validate_binance_api_key(exchange):
        print("Invalid Binance Futures API key.")
        use_binance_futures = False

@app.route('/webhook', methods=['POST'])
def webhook():
    print("🚨 Alerta recebido!")
    try:
        data = json.loads(request.data)
        print("🔎 Dados recebidos:", data)
    except Exception as e:
        return {"status": "erro", "mensagem": f"Erro ao interpretar JSON: {str(e)}"}

    # Segurança com chave (se estiver configurada no config.json)
    if "key" in config and "key" in data:
        if str(data["key"]) != str(config["key"]):
            return {"status": "erro", "mensagem": "Chave inválida"}

    # Interpreta campos do alerta
    msg = data.get("msg", "").upper()
    symbol = data.get("ticker", "").replace(".P", "").replace("USDT", "USDT")  # limpa sufixo
    price = float(data.get("price", 0))

    # Define o valor da operação (0.50 usdt com alavancagem máxima)
    operation_value = 0.50

    # Cria objeto base para o bot
    trade_data = {
        "symbol": symbol,
        "valor_usdt": operation_value,
        "price": price  # valor atual da moeda
    }

    # Decide a ação com base no texto da mensagem
    if "HORA DE COMPRAR" in msg:
        trade_data["acao"] = "comprar"
        print("🟢 Entrando comprado em", symbol)

    elif "HORA DE VENDER" in msg:
        trade_data["acao"] = "vender"
        print("🔴 Entrando vendido em", symbol)

    elif "GAIN DE ALTA 3%" in msg:
        trade_data["acao"] = "parcial_compra"
        print("✅ Take parcial da compra em", symbol)

    elif "GAIN DE BAIXA 3%" in msg:
        trade_data["acao"] = "parcial_venda"
        print("✅ Take parcial da venda em", symbol)

    elif "GAIN EXTRA ALTA" in msg:
        trade_data["acao"] = "final_compra"
        print("🏁 Finalizando 5% restante da compra em", symbol)

    elif "GAIN EXTRA BAIXA" in msg:
        trade_data["acao"] = "final_venda"
        print("🏁 Finalizando 5% restante da venda em", symbol)

    elif "STOP H" in msg:
        trade_data["acao"] = "stop_compra"
        print("🛑 Stop na compra em", symbol)

    elif "STOP L" in msg:
        trade_data["acao"] = "stop_venda"
        print("🛑 Stop na venda em", symbol)

    else:
        print("⚠️ Mensagem não reconhecida:", msg)
        return {"status": "ignorado", "mensagem": "Tipo de alerta não identificado"}

    # Executa ação no robô
    if use_binance_futures:
        bot = Bot()
        bot.run(trade_data)
        return {"status": "sucesso", "mensagem": f"Ação '{trade_data['acao']}' executada para {symbol}"}
    else:
        return {"status": "erro", "mensagem": "Binance Futures não habilitado"}

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000, debug=False)



