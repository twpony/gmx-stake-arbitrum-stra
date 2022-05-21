import brownie
from brownie import *
from helpers.constants import MaxUint256
from helpers.SnapshotManager import SnapshotManager
from helpers.time import days
from _setup.config import (
    ESGMXADDR,
)
from rich.console import Console
console = Console()


"""
  TODO: Put your tests here to prove the strat is good!
  See test_harvest_flow, for the basic tests
  See test_strategy_permissions, for tests at the permissions level
"""

def test_strategy_usage(deployer, vault, strategy, want, keeper):
      snap = SnapshotManager(vault, strategy, "StrategySnapshot")
      startingBalance = want.balanceOf(deployer)
      depositAmount = startingBalance 
      assert depositAmount >= 0

      want.approve(vault, MaxUint256, {"from": deployer})
      snap.settDeposit(depositAmount, {"from": deployer})

      vaultBalanceBefore = vault.balance()

      shares = vault.balanceOf(deployer)
      assert want.balanceOf(vault) > 0

      # Earn
      snap.settEarn({"from": keeper})

      chain.sleep(days(5))
      chain.mine(1)

      # harvest
      snap.settHarvest({"from": keeper})
      # tend
      snap.settTend({"from": keeper})


      chain.sleep(days(5))
      chain.mine(1)

      # harvest
      snap.settHarvest({"from": keeper})
      # tend
      snap.settTend({"from": keeper})
      

      chain.sleep(days(5))
      chain.mine(1)

      # harvest
      snap.settHarvest({"from": keeper})

      vaultBalanceAfter = vault.balance()

      # withdraw all
      snap.settWithdrawAll({"from": deployer})
      
      # calculate Vault APY
      profit = vaultBalanceAfter - vaultBalanceBefore
      profitRate = (profit / vaultBalanceBefore)*100
      profitRateAPY = profitRate * 365 /15

      # calculate Vault APY including unrealized ESGMX
      esGMX = interface.IERC20Detailed(ESGMXADDR)
      leftESGMX = esGMX.balanceOf(strategy)
      allprofitrate = (leftESGMX + profit) / vaultBalanceBefore * 100
      allAPY = allprofitrate * 365 / 15

      print("================== APY (test for 15 days) ==================")
      print("Realized APY:  ", profitRateAPY)
      print("All APY (including unrealized ESGMX):   ", allAPY)








