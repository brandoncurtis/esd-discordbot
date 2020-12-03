#!/usr/bin/env python

import requests
import datetime
import time
import random
import asyncio
import discord
import os
from discord.ext.commands import Bot
from discord.ext import commands, tasks
from web3 import Web3
from dotenv import load_dotenv

load_dotenv(override=True)
DISCORD_WEBHOOK_URL = os.getenv("WEBHOOK_URL")
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
NODE_URL = os.getenv("NODE_URL")
START_BLOCK = os.getenv("START_BLOCK")
TOKEN_ABI = os.getenv("TOKEN_ABI")
UNIROUTER_ADDR = os.getenv("UNIROUTER_ADDR")
UNIROUTER_ABI = os.getenv("UNIROUTER_ABI")
UNIPOOL_ABI = os.getenv("UNIPOOL_ABI")
ZERO_ADDR = '0x0000000000000000000000000000000000000000'
ONE_18DEC = 1000000000000000000
ONE_6DEC = 1000000
MAIN_BASETOKEN = 'ESD'

CIRCULATING_EXCLUDED = {
            'MPH': [
                '0xd48Df82a6371A9e0083FbfC0DF3AF641b8E21E44',
                '0x56f34826Cc63151f74FA8f701E4f73C5EAae52AD',
                '0xfecBad5D60725EB6fd10f8936e02fa203fd27E4b',
                '0x8c5ddBB0fd86B6480D81A1a5872a63812099C043',
            ]
            }

w3 = Web3(Web3.HTTPProvider(NODE_URL))

client = discord.Client(command_prefix='!')
activity_start = discord.Streaming(name='bot startup',url='https://etherscan.io/address/0x284fa4627AF7Ad1580e68481D0f9Fc7e5Cf5Cf77')

update_index = 0

ASSETS = {
    'ESD': {
        'addr':'0x36F3FD68E7325a35EB768F1AedaAe9EA0689d723',
        'main_quotetoken':'USDC',
        'pools': {
            'USDC': {
                'router':UNIROUTER_ADDR,
                'addr':'0x88ff79eB2Bc5850F27315415da8685282C7610F9',
                'basetoken_index': 0,
                'quotetoken_index': 1,
                'rewards':'0x4082D11E506e3250009A991061ACd2176077C88f',
                'oracles': [],
                #'oracle': [
                #    {'addr':'0xB4e16d0168e52d35CaCD2c6185b44281Ec28C9Dc','type':'mult',}
                #    {'addr':'0xB4e16d0168e52d35CaCD2c6185b44281Ec28C9Dc','type':'div',}
                #    ],
                },
            },
        },
}

@client.event
async def on_ready():
    print('We have logged in as {0.user}'.format(client))
    await client.change_presence(activity=activity_start)
    update_price.start()

@tasks.loop(seconds=20)
async def update_price():
    global update_index
    asset_list = list(ASSETS.keys())
    basetoken_name = asset_list[update_index % len(asset_list)]
    basetoken = ASSETS[basetoken_name]
    quotetoken_name = basetoken['main_quotetoken']
    pool = basetoken['pools'][quotetoken_name]
    basetoken_contract = w3.eth.contract(address=basetoken['addr'], abi=TOKEN_ABI)
    pool_contract = w3.eth.contract(address=pool['addr'], abi=UNIPOOL_ABI)
    quotetoken_addr = pool_contract.functions[f'token{pool["quotetoken_index"]}']().call()
    quotetoken_contract = w3.eth.contract(address=quotetoken_addr, abi=TOKEN_ABI)
    router_contract = w3.eth.contract(address=pool['router'], abi=UNIROUTER_ABI)

    # fetch pool state
    print(f'fetching pool reserves for {basetoken_name} ({basetoken["addr"]})...')
    poolvals = pool_contract.functions['getReserves']().call()
    #oraclevals = oracle_contract.functions['getReserves']().call()
    
    # calculate price
    print(f'calculating price...')
    atoms_per_basetoken = 10**basetoken_contract.functions['decimals']().call()
    atoms_per_quotetoken = 10**quotetoken_contract.functions['decimals']().call()
    token_price = router_contract.functions['quote'](atoms_per_basetoken, poolvals[0], poolvals[1]).call() / atoms_per_quotetoken
    oracle_price = 1
    for oracle in pool['oracles']:
        oracle_contract = w3.eth.contract(address=oracle['addr'])
        oracle_reserves = oracle_contract.functions['getReserves']().call()
        atoms_per_oracle_token0 = 10**w3.eth.contract(address=oracle_contract.functions['token0']().call()).functions['decimals']().call()
        atoms_per_oracle_token1 = 10**w3.eth.contract(address=oracle_contract.functions['token1']().call()).functions['decimals']().call()
        oracle_price_step = oracle_price * router_contract.functions['quote'](ONE_6DEC, oraclevals[0], oraclevals[1]).call()*10**-18
        if oracle['type'] == 'div':
            oracle_price_step = oracle_price_step ** -1
        oracle_price = oracle_price * oracle_price_step
    print(f'oracle price: {oracle_price}')
    price = token_price * oracle_price

    # update price
    print(f'updating the price...')
    msg = f'${price:0.4f} {basetoken_name}'
    new_price = discord.Streaming(name=msg,url=f'https://etherscan.io/token/basetoken["addr"]')
    print(msg)
    await client.change_presence(activity=new_price)
    update_index += 1

@client.event
async def on_message(msg):
    if client.user.id != msg.author.id: # and msg.channel.id == 775798003960643634:
        if '!foo' in msg.content:
            await msg.channel.send('bar')
#        elif '!bot' in msg.content:
#            embed = discord.Embed(
#                    title='80s-themed AI assistant, at your service :sparkles:',
#                    description=f':arrows_counterclockwise: `!reboot` info on the MPH88 reboot\n'
#                                f':bar_chart: `!uniswap`: MPH markets and trading\n'
#                                f':potable_water: `!supply`: MPH max and circulating supply\n'
#                                f':thinking: `!incentives`: information on staking and liquidity rewards\n'
#                                f':globe_with_meridians: `!contribute`: contribute to the community wiki (coming soon)\n'
#                                f':chart_with_upwards_trend: improve me on GitHub (coming soon)'
#                    )
#            await msg.channel.send(embed=embed)
#        elif '!reboot' in msg.content:
#            embed = discord.Embed(
#                    title='88MPH is being rebooted on November 19th',
#                    description=f'**WHY:** two exploits; funds taken in the 1st exploit were reclaimed in the 2nd\n'
#                                f'**HOW:** releasing a new MPH token based on a snapshot before the 2nd exploit\n'
#                                f'**WHAT:** read announcements to [claim MPH](https://88mph.app/claim-mph) ([+ETH for LPs](https://88mph.app/claim-eth)) from the snapshot\n'
#                                f'**WHEN:** farming restarts Nov 20th 20:00 GMT; capital deposits will reopen in a few days\n'
#                                f'`NOTE!` when LPs claim ETH, it is in WETH form; [unwrap to ETH here](https://matcha.xyz/markets/ETH/WETH)\n'
#                                f'`NOTE!` [old MPH](https://etherscan.io/token/{ASSETS["oldMPH"]["addr"]}) no longer has value.\n'
#                                f'address of new MPH: [{ASSETS["MPH"]["addr"]}](https://etherscan.io/token/{ASSETS["MPH"]["addr"]})'
#                    )
#            await msg.channel.send(embed=embed)
        elif '!ap' in msg.content:
            val = float(msg.content.split(' ')[-1])
            # APY = (1 + APR / n) ** n - 1
            APYfromAPR_daily = 100 * ((1 + val / (100 * 365)) ** 365 - 1)
            APYfromAPR_weekly = 100 * ((1 + val / (100 * 52)) ** 52 - 1)
            # APR = n * (1 + APY) ** (1 / n) -n
            APRfromAPY_daily = 100 * (365 * ((1 + val / 100) ** (1 / 365)) - 365)
            APRfromAPY_weekly = 100 * (52 * ((1 + val / 100) ** (1 / 52)) - 52)
            embed = discord.Embed(
                    title=':man_teacher: **Convert between APR and APY?**',
                    )
#            embed.add_field(name = 'Compounded Daily', value = 'If you redeem and reinvest rewards daily...', inline=False)
#            embed.add_field(
#                    name = f'APR to APY',
#                    value = f'{val:,.2f}% APR is equal to {APYfromAPR_daily:,.2f}% APY. $1000 will make about ${1000*val/100/365:,.2f} per day.',
#                    inline = True
#                    )
#            embed.add_field(
#                    name = f'APY to APR',
#                    value = f'{val:,.2f}% APY is equal to {APRfromAPY_daily:,.2f}% APR. $1000 will make about ${1000*APRfromAPY_daily/100/365:,.2f} per day.',
#                    inline = True
#                    )
            embed.add_field(name = 'Compounded Weekly', value = 'If you redeem and reinvest rewards weekly...', inline=False)
            embed.add_field(
                    name = f'APR to APY',
                    value = f'{val:,.2f}% APR is equal to {APYfromAPR_weekly:,.2f}% APY. $1000 will make about ${1000*val/100/365:,.2f} per day.',
                    inline = True
                    )
            embed.add_field(
                    name = f'APY to APR',
                    value = f'{val:,.2f}% APY is equal to {APRfromAPY_weekly:,.2f}% APR. $1000 will make about ${1000*APRfromAPY_weekly/100/365:,.2f} per day.',
                    inline = True
                    )
            await msg.channel.send(embed=embed)
        elif '!uniswap' in msg.content:
            asset = MAIN_BASETOKEN
            uni_addr, uni_deposit_token, uni_deposit_pairing, uni_token_frac = get_uniswapstate(asset)
            embed = discord.Embed(
                    title=f':mag: {asset} Uniswap Pool',
                    description=f':bank: Uniswap contract: [{uni_addr}](https://etherscan.io/address/{uni_addr})\n'
                                f':moneybag: Liquidity: `{uni_deposit_token:,.2f}` {asset} (`{100*uni_token_frac:.2f}%` of supply), `{uni_deposit_pairing:,.2f}` USDC\n'
                                f':arrows_counterclockwise: [Trade {asset}](https://app.uniswap.org/#/swap?outputCurrency={ASSETS[asset]["addr"]}), '
                                f'[Add Liquidity](https://app.uniswap.org/#/add/0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48/{ASSETS[asset]["addr"]}), '
                                f'[Remove Liquidity](https://app.uniswap.org/#/remove/0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48/{ASSETS[asset]["addr"]})\n'
                                f':bar_chart: [{asset}:USDC Uniswap chart](https://www.dextools.io/app/uniswap/pair-explorer/{uni_addr})'
                    )
            await msg.channel.send(embed=embed)
#        elif '!incentives' in msg.content or '!farm' in msg.content:
#            embed = discord.Embed(
#                    title='How do I farm 88MPH?',
#                    description=f'**Short term:** provide liquidity in the ETH:MPH Uniswap pool (14 days, starts Nov 20th 20:00 GMT)\n'
#                                f'**Long term:** stake MPH to receive a share of investment profits\n'
#                                f'**Alternative:** deposit funds to receive MPH; 90% must be paid back to withdraw!\n'
#                                f'(early withdrawals require up to 100% payback of received MPH)'
#                    )
#            await msg.channel.send(embed=embed)
#        elif '!supply' in msg.content:
#            asset = 'MPH'
#            supply = get_supply('MPH')
#            circulating = get_supply_circulating('MPH')
#            circulating_frac = circulating / supply
#            uni_supply = get_supply('MPH', ASSETS[asset]['pool'])
#            uni_supply_frac = uni_supply / supply
#            embed = discord.Embed(
#                    title=f':bar_chart: Current and maximum supply of MPH?',
#                    description=f'**Max Supply:** maximum supply is unlimited\n'
#                    f'**Total Supply:** `{supply:,.2f}` {asset}, `{uni_supply:,.2f}` {asset} (`{100*uni_supply_frac:.2f}%`) in Uniswap\n'
#                    f'**Circulating:** `{circulating:,.2f}` {asset} (`{100*circulating_frac:.2f}%`)\n'
#                    f'**Distribution:** by liquidity mining and to capital depositors\n'
#                    f'90% of deposit incentives are paid back to the Treasury at redemption;\n'
#                    f'the community can decide to issue more incentives, pay for development, burn...'
#                    )
#            await msg.channel.send(embed=embed)
#        else:
#            return

def get_supply_circulating(asset):
    token_contract = w3.eth.contract(address=ASSETS[asset]['addr'], abi=UNIPOOL_ABI)
    token_decimals = token_contract.functions['decimals']().call()
    token_totalsupply = token_contract.functions['totalSupply']().call()*10**(-1*token_decimals)
    token_circulating = token_totalsupply
    for excluded_addr in CIRCULATING_EXCLUDED[asset]:
        token_circulating = token_circulating - token_contract.functions['balanceOf'](excluded_addr).call()*10**(-1*token_decimals)
    return token_circulating

def get_supply(asset, address=''):
    token_contract = w3.eth.contract(address=ASSETS[asset]['addr'], abi=UNIPOOL_ABI)
    atoms_per_token = 10 ** token_contract.functions['decimals']().call()
    if address != '':
        token_balance = token_contract.functions['balanceOf'](address).call() / atoms_per_token
        return token_balance
    else: 
        token_totalsupply = token_contract.functions['totalSupply']().call() / atoms_per_token
        return token_totalsupply

def get_uniswapstate(asset):
    basetoken_name = asset
    basetoken = ASSETS[basetoken_name]
    quotetoken_name = basetoken['main_quotetoken']
    pool = basetoken['pools'][quotetoken_name]
    pool_contract = w3.eth.contract(address=pool['addr'], abi=UNIPOOL_ABI)
    basetoken_contract = w3.eth.contract(address=basetoken['addr'], abi=TOKEN_ABI)
    quotetoken_addr = pool_contract.functions[f'token{pool["quotetoken_index"]}']().call()
    quotetoken_contract = w3.eth.contract(address=quotetoken_addr, abi=TOKEN_ABI)
    atoms_per_basetoken = 10**basetoken_contract.functions['decimals']().call()
    atoms_per_quotetoken = 10**quotetoken_contract.functions['decimals']().call()
    pool_deposits = pool_contract.functions['getReserves']().call()
    pool_basetoken_deposits = pool_deposits[pool['basetoken_index']] / atoms_per_basetoken
    pool_quotetoken_deposits = pool_deposits[pool['quotetoken_index']] / atoms_per_quotetoken
    basetoken_totalsupply = get_supply(basetoken_name)
    pool_basetoken_supplyfrac = pool_basetoken_deposits / basetoken_totalsupply
    return (pool['addr'], pool_basetoken_deposits, pool_quotetoken_deposits, pool_basetoken_supplyfrac)

def get_profitsharestate():
    ps_address = vault_addr['profitshare']['addr']
    ps_contract = w3.eth.contract(address=ps_address, abi=PS_ABI)
    lp_addr = ps_contract.functions['lpToken']().call()
    lp_contract = w3.eth.contract(address=lp_addr, abi=VAULT_ABI)
    ps_decimals = lp_contract.functions['decimals']().call()
    lp_totalsupply = lp_contract.functions['totalSupply']().call()*10**(-1*ps_decimals)
    ps_rewardrate = ps_contract.functions['rewardRate']().call()
    ps_totalsupply = ps_contract.functions['totalSupply']().call()*10**(-1*ps_decimals)
    ps_rewardfinish = ps_contract.functions['periodFinish']().call()
    ps_rewardperday = ps_rewardrate * 3600 * 24 * 10**(-1*ps_decimals)
    ps_rewardfinishdt = datetime.datetime.fromtimestamp(ps_rewardfinish)
    ps_stake_frac = ps_totalsupply / lp_totalsupply
    return (ps_totalsupply, ps_rewardperday, ps_rewardfinishdt, ps_stake_frac)

def get_vaultstate(vault):
    vault_address = vault_addr[vault]['addr']
    vault_contract = w3.eth.contract(address=vault_address, abi=VAULT_ABI)
    vault_strat = vault_contract.functions['strategy']().call()
    vault_strat_future = vault_contract.functions['futureStrategy']().call()
    vault_strat_future_time = int(vault_contract.functions['strategyUpdateTime']().call())
    vault_decimals = int(vault_contract.functions['decimals']().call())
    vault_shareprice = vault_contract.functions['getPricePerFullShare']().call()*10**(-1*vault_decimals)
    vault_total = vault_contract.functions['underlyingBalanceWithInvestment']().call()*10**(-1*vault_decimals)
    vault_buffer = vault_contract.functions['underlyingBalanceInVault']().call()*10**(-1*vault_decimals)
    vault_target_numerator = vault_contract.functions['vaultFractionToInvestNumerator']().call()
    vault_target_denominator = vault_contract.functions['vaultFractionToInvestDenominator']().call()
    vault_target = vault_target_numerator / vault_target_denominator
    return (vault_address, vault_shareprice, vault_total, vault_buffer, vault_target, vault_strat, vault_strat_future, vault_strat_future_time)

def main():
    print(f'starting discord bot...')
    client.run(DISCORD_BOT_TOKEN)
    print(f'discord bot started')

if __name__ == '__main__':
    main()
