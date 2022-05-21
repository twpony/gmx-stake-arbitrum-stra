from helpers.StrategyCoreResolver import StrategyCoreResolver
from rich.console import Console
from helpers.utils import (
    approx,
)

console = Console()


class StrategyResolver(StrategyCoreResolver):
    def get_strategy_destinations(self):
        """
        Track balances for all strategy implementations
        (Strategy Must Implement)
        """
        strategy = self.manager.strategy
        return {}

    def hook_after_confirm_withdraw(self, before, after, params):
        """
        Specifies extra check for ordinary operation on withdrawal
        Use this to verify that balances in the get_strategy_destinations are properly set
        """
        assert True

    def hook_after_confirm_deposit(self, before, after, params):
        """
        Specifies extra check for ordinary operation on deposit
        Use this to verify that balances in the get_strategy_destinations are properly set
        """
        assert True  ## Done in earn

    def hook_after_earn(self, before, after, params):
        """
        Specifies extra check for ordinary operation on earn
        Use this to verify that balances in the get_strategy_destinations are properly set
        """
        # stake in GMX
        # to check want balance and feeTracker balance
        
        assert after.balances("feeGmxTracker", "strategy") > before.balances("feeGmxTracker", "strategy")
        
        fTrackerChange = after.balances("feeGmxTracker", "strategy") - before.balances("feeGmxTracker", "strategy")
        
        wantSettChange = before.balances("want", "sett") - after.balances("want", "sett") 

        assert fTrackerChange == wantSettChange
 
        depositsgTrackerChange = after.depositBalances("sgTracker") - before.depositBalances("sgTracker")

        assert depositsgTrackerChange == fTrackerChange

    def hook_after_harvest(self, before, after):
        # harvest weth
        assert after.balances("weth", "strategy") >= before.balances("weth", "strategy")

        # harvest ESGMX
        assert after.balances("esgmx", "strategy") >= before.balances("esgmx", "strategy")

        # harvest GMX
        assert after.balances("want", "strategy") >= before.balances("want", "strategy")


    def confirm_tend(self, before, after, tx):
        """
        Tend Should;
        - Increase the number of staked tended tokens in the strategy-specific mechanism
        - Reduce the number of tended tokens in the Strategy to zero

        (Strategy Must Implement)
        """
        # vest ESGMX
        esgmxChange = before.balances("esgmx", "strategy") - after.balances("esgmx", "strategy")
        vesterChange = after.balances("GmxVester", "strategy") - before.balances("GmxVester", "strategy")
        assert approx(esgmxChange, vesterChange, 1)

        # stake GMX
        gmxChange = before.balances("want", "strategy") - after.balances("want", "strategy")
        fTrackerChange = after.balances("feeGmxTracker", "strategy") - before.balances("feeGmxTracker", "strategy")
        if vesterChange == 0:
            assert approx(gmxChange, fTrackerChange, 1)

        # some fTracker maybe transfer to Vester
        if vesterChange > 0:      
            assert gmxChange >= fTrackerChange
