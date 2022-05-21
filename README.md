
# GMX-Stake-Arbitrum-Strategy

**1. Introduction**

This strategy's want token is GMX. It will  [stake GMX](https://gmx.io/earn) on this platform. [GMX ](https://gmx.io/)is the decentralized exchange platform running on Arbitrum. 

The rewards from GMX are ESGMX and WETH. Because ESGMX cannot be transferred （here is the explanation: [Rewards - GMX (gitbook.io)](https://gmxio.gitbook.io/gmx/rewards#escrowed-gmx)）,  so after achieving the rewards, this strategy will vest ESGMX in [Vester](https://arbiscan.io/address/0x199070DDfd1CFb69173aa2F7e20906F26B363004#code) to exchange ESGMX to GMX. There is the third reward [BNGMX](https://gmxio.gitbook.io/gmx/rewards#multiplier-points). After claiming, this reward can be exchanged to WETH. 

WETH will be swapped to GMX by [ETH/GMX Uniswap V3 Pool](https://info.uniswap.org/#/arbitrum/pools/0x80a9ae39310abf666a87c743d6ebbd0e8c42158e) on Arbitrum.

This strategy is developed on [badger-vaults-mix-v1.5](https://github.com/Badger-Finance/badger-vaults-mix-v1.5) template. 

**2. APY**

I test my strategy on Arbitrum-mainnet-forked by brownie. The **realized APY is 5.41%**. The **APY (including ESGMX) is about 21.4%**. So the profit looks fine. If you wanna realize all profit, you should stake GMX for one year.  

The profit test code refter to `test/test_custom.py`.

**3. Strategy Diagram**

![gmx-stake-arbitrum-stra](https://github.com/twpony/file/blob/main/gmxstakestra.png)



# Usage

1) Install all dependencies according to Readme on [badger-vaults-mix-v1.5](https://github.com/Badger-Finance/badger-vaults-mix-v1.5).
2) Enter the python virtual environment:  `source ven/bin/activate`
3) `brownie compile`
4)  `brownie test --interactive`

# Tips
Open two terminal in VScode, otherwise may have RPC connection error

One terminal runs `ganache-cli --accounts 10 --fork https://arb1.arbitrum.io/rpc --mnemonic brownie --port 8545 --chainId 42161 --hardfork istanbul`

The other terminal runs `brownie test --interactive`







