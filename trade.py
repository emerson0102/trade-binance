from binance.exceptions import BinanceAPIException # type: ignore
from binance.client import Client # type: ignore
from binance.enums import * # type: ignore
from dotenv import load_dotenv # type: ignore
import os
import time
import numpy as np # type: ignore
import math

# Carregar variáveis de ambiente do arquivo .env
load_dotenv()

# Carregar chaves da API
api_key = os.getenv("BINANCE_API_KEY")
api_secret = os.getenv("BINANCE_API_SECRET")

# Inicializar o cliente Binance
client = Client(api_key, api_secret)

# Função para sincronizar o tempo local com o servidor Binance
def sincronizar_tempo_binance(client):
    try:
        server_time = client.get_server_time()
        local_time = int(time.time() * 1000)
        diff = server_time['serverTime'] - local_time
        print(f"Sincronizando relógio com diferença de {diff}ms")
        return diff
    except BinanceAPIException as e:
        print(f"Erro ao sincronizar tempo: {e}")
        return 0

time_offset = sincronizar_tempo_binance(client)

# Função para ajustar a quantidade com base no stepSize
def ajustar_quantidade(quantidade, step_size):
    precision = int(round(-math.log(step_size, 10), 0))
    return float(f"{quantidade:.{precision}f}")

# Função para obter o stepSize do par
def obter_step_size(par):
    try:
        info = client.get_exchange_info()
        for filtro in info['symbols']:
            if filtro['symbol'] == par:
                step_size = next(
                    f['stepSize'] for f in filtro['filters'] if f['filterType'] == 'LOT_SIZE'
                )
                return float(step_size)
        print(f"Step size não encontrado para {par}.")
        return None
    except Exception as e:
        print(f"Erro ao obter step size: {e}")
        return None

# Função para obter o preço atual do par de moedas
def obter_preco_atual(par):
    try:
        preco = client.get_symbol_ticker(symbol=par)
        return float(preco['price']) if preco and 'price' in preco else None
    except Exception as e:
        print(f"Erro ao obter preço: {e}")
        return None

# Função para obter os preços históricos
def obter_precos_historicos(par, intervalo='15m', limit=100):
    try:
        candles = client.get_klines(symbol=par, interval=intervalo, limit=limit)
        precos = [float(candle[4]) for candle in candles]  # Preço de fechamento
        return precos
    except Exception as e:
        print(f"Erro ao obter preços históricos: {e}")
        return []

# Função para calcular a EMA
def calcular_ema(precos, periodo):
    if len(precos) < periodo:
        raise ValueError("Número de preços insuficiente para calcular a EMA.")

    # Inicializar a EMA com a média simples dos primeiros 'periodo' preços
    ema_inicial = np.mean(precos[:periodo])

    # Fator de suavização
    k = 2 / (periodo + 1)

    # Aplicar fórmula recursiva
    ema = ema_inicial
    for preco in precos[periodo:]:
        ema = (preco * k) + (ema * (1 - k))

    return ema

# Função para comprar moeda
def comprar_moeda(par, capital_usdt):
    try:
        preco_atual = obter_preco_atual(par)
        if not preco_atual:
            print("Erro ao obter o preço atual para compra.")
            return

        step_size = obter_step_size(par)
        if not step_size:
            print("Step size não encontrado. Abortando compra.")
            return

        quantidade = capital_usdt / preco_atual
        quantidade_ajustada = ajustar_quantidade(quantidade, step_size)

        order = client.order_market_buy(
            symbol=par,
            quantity=quantidade_ajustada
        )
        print(f"Compra realizada com sucesso: {order}")
    except BinanceAPIException as e:
        print(f"Erro da API Binance ao realizar a compra: {e}")
    except Exception as e:
        print(f"Erro ao realizar a compra: {e}")

# Função para vender moeda
def vender_moeda(par, quantidade):
    try:
        step_size = obter_step_size(par)
        if not step_size:
            print("Step size não encontrado. Abortando venda.")
            return

        quantidade_ajustada = ajustar_quantidade(quantidade, step_size)

        order = client.order_market_sell(
            symbol=par,
            quantity=quantidade_ajustada
        )
        print(f"Venda realizada com sucesso: {order}")
    except BinanceAPIException as e:
        print(f"Erro da API Binance ao realizar a venda: {e}")
    except Exception as e:
        print(f"Erro ao realizar a venda: {e}")

# Função para obter saldo de um ativo
def obter_quantidade(ativo):
    try:
        saldo = client.get_asset_balance(asset=ativo)
        if saldo and 'free' in saldo:
            quantidade = float(saldo['free'])
            print(f"Saldo disponível de {ativo}: {quantidade}")
            return quantidade
        else:
            print(f"Saldo não encontrado para {ativo}.")
            return 0.0
    except Exception as e:
        print(f"Erro ao obter saldo de {ativo}: {e}")
        return 0.0

# Função principal para monitorar o mercado
def monitorar_mercado(capital_inicial, par, intervalo=20):
    moeda_base = par.replace("USDT", "")  # Exemplo: ETH em ETHUSDT
    saldo_inicial = obter_quantidade(moeda_base)
    posicao_comprada = saldo_inicial > 0
    
    if posicao_comprada:
        print(f"Já existe uma posição comprada com saldo de {saldo_inicial} {moeda_base}.")
    else:
        print("Nenhuma posição comprada detectada. Pronto para iniciar operações.")
    
    while True:
        precos = obter_precos_historicos(par)
        if len(precos) < 26:
            print("Dados históricos insuficientes.")
            time.sleep(intervalo)
            continue

        ema_curta = calcular_ema(precos, 12)
        ema_longa = calcular_ema(precos, 26)
        
        print(f"EMA Curta: {ema_curta} | EMA Longa: {ema_longa}")

        if ema_curta < ema_longa and posicao_comprada:
            saldo = obter_quantidade(moeda_base)
            if saldo > 0:
                vender_moeda(par, saldo)
                posicao_comprada = False
        
        if ema_curta > ema_longa and not posicao_comprada:
            comprar_moeda(par, capital_inicial)
            posicao_comprada = True

        print(f"Monitorando o mercado... Próxima verificação em {intervalo} segundos.")
        time.sleep(intervalo)

# Configuração inicial
par_moeda = "ETHUSDT"
capital_inicial = 20  # USDT
monitorar_mercado(capital_inicial, par_moeda)
