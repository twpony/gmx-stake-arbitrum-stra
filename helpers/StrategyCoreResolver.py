from brownie import *
from decimal import Decimal
from helpers.shares_math import (
    get_withdrawal_fees_in_shares,
    get_withdrawal_fees_in_want,
    from_shares_to_want,
    get_report_fees,
)

from helpers.utils import (
    approx,
)
from helpers.constants import *
from helpers.multicall import Call, as_wei, func
from rich.console import Console

console = Console()


class StrategyCoreResolver:
    def __init__(self, manager):
        self.manager = manager

    # ===== Read strategy data =====

    def add_entity_shares_for_tokens(self, calls, tokenKey, token, entities):
        for entityKey, entity in entities.items():
            calls.append(
                Call(
                    token.address,
                    [func.digg.sharesOf, entity],
                    [["shares." + tokenKey + "." + entityKey, as_wei]],
                )
            )

        return calls

    def add_entity_balances_for_tokens(self, calls, tokenKey, token, entities):
        for entityKey, entity in entities.items():
            calls.append(
                Call(
                    token.address,
                    [func.erc20.balanceOf, entity],
                    [["balances." + tokenKey + "." + entityKey, as_wei]],
                )
            )

        return calls

    # custom test
    def add_sgTracker_snap(self, calls, sgTrackerAddr, addrA, addrB, tokenKey):
        calls.append(
                Call(
                    sgTrackerAddr,
                    [func.stakedGmxTracker.depositBalances, addrA, addrB],
                    [["depositBalances." + tokenKey, as_wei]],
                )
        )
        return calls

    def add_balances_snap(self, calls, entities):
        want = self.manager.want
        sett = self.manager.sett

        # cutstom test
        esgmx = self.manager.esgmx
        stakedGmxTracker = self.manager.stakedGmxTracker
        feeGmxTracker = self.manager.feeGmxTracker
        GmxVester = self.manager.GmxVester
        weth = self.manager.weth

        calls = self.add_entity_balances_for_tokens(calls, "want", want, entities)
        calls = self.add_entity_balances_for_tokens(calls, "sett", sett, entities)

        # cutstom test
        calls = self.add_entity_balances_for_tokens(calls, "esgmx", esgmx, entities)
        calls = self.add_entity_balances_for_tokens(calls, "stakedGmxTracker", stakedGmxTracker, entities)
        calls = self.add_entity_balances_for_tokens(calls, "feeGmxTracker", feeGmxTracker, entities)
        calls = self.add_entity_balances_for_tokens(calls, "GmxVester", GmxVester, entities)
        calls = self.add_entity_balances_for_tokens(calls, "weth", weth, entities)
        
        return calls

    def add_sett_snap(self, calls):
        sett = self.manager.sett

        calls.append(
            Call(sett.address, [func.sett.balance], [["sett.balance", as_wei]])
        )
        calls.append(
            Call(sett.address, [func.sett.available], [["sett.available", as_wei]])
        )
        calls.append(
            Call(
                sett.address,
                [func.sett.getPricePerFullShare],
                [["sett.getPricePerFullShare", as_wei]],
            )
        )
        calls.append(
            Call(sett.address, [func.erc20.decimals], [["sett.decimals", as_wei]])
        )
        calls.append(
            Call(sett.address, [func.erc20.totalSupply], [["sett.totalSupply", as_wei]])
        )
        calls.append(
            Call(
                sett.address,
                [func.sett.withdrawalFee],
                [["sett.withdrawalFee", as_wei]],
            )
        )
        calls.append(
            Call(
                sett.address,
                [func.sett.managementFee],
                [["sett.managementFee", as_wei]],
            )
        )
        calls.append(
            Call(
                sett.address,
                [func.sett.lastHarvestedAt],
                [["sett.lastHarvestedAt", as_wei]],
            )
        )
        calls.append(
            Call(
                sett.address,
                [func.sett.performanceFeeGovernance],
                [["sett.performanceFeeGovernance", as_wei]],
            )
        )
        calls.append(
            Call(
                sett.address,
                [func.sett.performanceFeeStrategist],
                [["sett.performanceFeeStrategist", as_wei]],
            )
        )

        return calls

    def add_strategy_snap(self, calls, entities=None):
        strategy = self.manager.strategy

        calls.append(
            Call(
                strategy.address,
                [func.strategy.balanceOfPool],
                [["strategy.balanceOfPool", as_wei]],
            )
        )
        calls.append(
            Call(
                strategy.address,
                [func.strategy.balanceOfWant],
                [["strategy.balanceOfWant", as_wei]],
            )
        )
        calls.append(
            Call(
                strategy.address,
                [func.strategy.balanceOf],
                [["strategy.balanceOf", as_wei]],
            )
        )

        return calls        


    # ===== Verify strategy action results =====

    def confirm_harvest_state(self, before, after, tx):
        """
        Confirm the events from the harvest match with actual recorded change
        Must be implemented on a per-strategy basis
        """
        self.printHarvestState({}, [])
        return True

    def printHarvestState(self, event, keys):
        return True

    def confirm_earn(self, before, after, params):
        """
        Earn Should:
        - Decrease the balanceOf() want in the Sett
        - Increase the balanceOf() want in the Strategy
        - Increase the balanceOfPool() in the Strategy
        - Reduce the balanceOfWant() in the Strategy to zero
        - Users balanceOf() want should not change
        """

        console.print("=== Compare Earn ===")
        self.manager.printCompare(before, after)

        # Do nothing if there is not enough available want in sett to transfer.
        # NB: Since we calculate available want by taking a percentage when
        # balance is 1 it gets rounded down to 1.
        if before.balances("want", "sett") <= 1:
            return

        assert after.balances("want", "sett") <= before.balances("want", "sett")

        # All want should be in pool OR sitting in strategy, not a mix
        assert (
            after.get("strategy.balanceOfWant") == 0
            and after.get("strategy.balanceOfPool")
            > before.get("strategy.balanceOfPool")
        ) or (
            after.get("strategy.balanceOfWant") > before.get("strategy.balanceOfWant")
            and after.get("strategy.balanceOfPool") == 0
        )

        assert after.get("strategy.balanceOf") > before.get("strategy.balanceOf")
        assert after.balances("want", "user") == before.balances("want", "user")

        self.hook_after_earn(before, after, params)

    def confirm_withdraw(self, before, after, params, tx):
        """
        Withdraw Should;
        - Decrease the totalSupply() of Sett tokens
        - Decrease the balanceOf() Sett tokens for the user based on withdrawAmount and pricePerFullShare
        - Decrease the balanceOf() want in the Strategy
        - Decrease the balance() tracked for want in the Strategy
        - Decrease the available() if it is not zero
        """

        console.print("=== Compare Withdraw ===")
        self.manager.printCompare(before, after)

        if params["amount"] == 0:
            # NOTE: withdraw(0) reverts so this should never be hit
            assert after.get("sett.totalSupply") == before.get("sett.totalSupply")
            # Decrease the Sett tokens for the user based on withdrawAmount and pricePerFullShare
            assert after.balances("sett", "user") == before.balances("sett", "user")
            return

        shares_to_burn = params["amount"]
        ppfs_before_withdraw = before.get("sett.getPricePerFullShare")
        vault_decimals = before.get("sett.decimals")

        # We check 4 things:
        # 1. burn() works properly
        # 2. strategy withdraws accurate amount
        # 3. withdrawal fee is calculated properly
        # 4. user gets back ~correct amount/something

        # 1.
        # Decrease the totalSupply of Sett tokens
        assert approx(
            after.get("sett.totalSupply") + shares_to_burn,
            before.get("sett.totalSupply"),
            1,
        )

        assert approx(
            after.balances("sett", "user") + shares_to_burn,
            before.balances("sett", "user"),
            1,
        )

        # 2.
        ## Accurately check user got the expected amount
        # Amount of want expected to be withdrawn
        expected_want = from_shares_to_want(
            shares_to_burn, ppfs_before_withdraw, vault_decimals
        )

        # Want in the strategy should be decreased, if idle in sett is insufficient to cover withdrawal
        if expected_want > before.balances("want", "sett"):
            # Withdraw from idle in sett first
            want_required_from_strat = expected_want - before.balances("want", "sett")

            # Ensure that we have enough in the strategy to satisfy the request
            assert want_required_from_strat <= before.get("strategy.balanceOf")

            # # NOTE: Assumes strategy don't lose > 1%
            # Strategies can lose money upto a certain threshold. On calling withdraw on a strategy
            # for some amount, we can only be sure that the strategy returns some minimum amount back
            # (based on a adjustable threshold parameter)

            # Strategy should get at least this amount of want after withdrawing from pool
            
            # after.get("strategy.balanceOf") is quite small, so change another method to check
            assert approx(
                before.get("strategy.balanceOf") ,
                after.get("strategy.balanceOf") + want_required_from_strat,
                1,
            )

        # 3.
        ## Accurately calculate withdrawal fee
        fee = fee_in_want = 0
        if before.get("sett.withdrawalFee") > 0:
            withdrawal_fee_bps = before.get("sett.withdrawalFee")
            total_supply_before_withdraw = before.get("sett.totalSupply")
            vault_balance_before_withdraw = before.get("sett.balance")

            fee = get_withdrawal_fees_in_shares(
                shares_to_burn,
                ppfs_before_withdraw,
                vault_decimals,
                withdrawal_fee_bps,
                total_supply_before_withdraw,
                vault_balance_before_withdraw,
            )

            fee_in_want = get_withdrawal_fees_in_want(
                shares_to_burn, ppfs_before_withdraw, vault_decimals, withdrawal_fee_bps
            )
            assert fee > 0 and fee_in_want > 0

        ## We got shares issued as expected
        """
            NOTE: We have to approx here
            We approx because for rounding we may get 1 less share
            >>> after.balances("sett", "treasury")
            399999999999999999
            >>> before.balances("sett", "treasury")
            200000000000000000
            >>> fee
            2e+17
        """
        # when withdraw all, left shares and balance is quite small
        # the fee shares calculation may have some deviation
        totalsupplytemp = total_supply_before_withdraw - shares_to_burn
        shareMintCheck = fee_in_want * totalsupplytemp / (after.get("sett.balance")-fee_in_want)
        shareIncrease = after.balances("sett", "treasury") - before.balances("sett", "treasury")
        assert approx(shareIncrease, shareMintCheck, 1)

        # 4.
        # # NOTE: Assumes strategy don't lose > 1%
        # Withdrawal increases user balance
        assert approx(
            after.balances("want", "user"),
            before.balances("want", "user") + expected_want - fee_in_want,
            1,
        )
        # Withdrawal should decrease balance of sett
        assert approx(
            before.get("sett.balance"),
            after.get("sett.balance") + expected_want - fee_in_want,
            1
        )
        # assert approx(
        #     after.get("sett.balance"),
        #     before.get("sett.balance") - expected_want + fee_in_want,
        #     1,
        # )

        self.hook_after_confirm_withdraw(before, after, params)

    def confirm_deposit(self, before, after, params):
        """
        Deposit Should;
        - Increase the totalSupply() of Sett tokens
        - Increase the balanceOf() Sett tokens for the user based on depositAmount / pricePerFullShare
        - Increase the balanceOf() want in the Sett by depositAmount
        - Decrease the balanceOf() want of the user by depositAmount
        """

        ppfs = before.get("sett.getPricePerFullShare")
        console.print("=== Compare Deposit ===")
        self.manager.printCompare(before, after)

        expected_shares = Decimal(params["amount"] * Wei("1 ether")) / Decimal(ppfs)
        if params.get("expected_shares") is not None:
            expected_shares = params["expected_shares"]

        # Increase the totalSupply() of Sett tokens
        assert approx(
            after.get("sett.totalSupply"),
            before.get("sett.totalSupply") + expected_shares,
            1,
        )

        # Increase the balanceOf() want in the Sett by depositAmount
        assert approx(
            after.balances("want", "sett"),
            before.balances("want", "sett") + params["amount"],
            1,
        )

        # Decrease the balanceOf() want of the user by depositAmount
        assert approx(
            after.balances("want", "user"),
            before.balances("want", "user") - params["amount"],
            1,
        )

        # Increase the balanceOf() Sett tokens for the user based on depositAmount / pricePerFullShare
        assert approx(
            after.balances("sett", "user"),
            before.balances("sett", "user") + expected_shares,
            1,
        )
        self.hook_after_confirm_deposit(before, after, params)

    # ===== Strategies must implement =====
    def get_strategy_destinations(self):
        """
        Track balances for all strategy implementations
        (Strategy Must Implement)
        """
        return {}

    ## NOTE: The ones below should be changed to assert False for the V1.5 Mix as the developer has to customize
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
        assert True

    def hook_after_earn(self, before, after, params):
        """
        Specifies extra check for ordinary operation on earn
        Use this to verify that balances in the get_strategy_destinations are properly set
        """
        assert True

    def confirm_harvest(self, before, after, tx):
        """
        Verfies that the Harvest produced yield and fees
        """
        # console.print("=== Compare Harvest ===")
        # self.manager.printCompare(before, after)
        # self.confirm_harvest_state(before, after, tx)

        ## Verify harvest, and verify that the correct amount of shares was issued against perf fees

        ## Simple check to guarantee a degree of gains
        valueGained = after.get("sett.getPricePerFullShare") > before.get(
            "sett.getPricePerFullShare"
        )

        # # Strategist should earn if fee is enabled and value was generated
        if before.get("sett.performanceFeeStrategist") > 0 and valueGained:
            assert after.balances("sett", "strategist") > before.balances(
                "sett", "strategist"
            )

        # # Strategist should earn if fee is enabled and value was generated
        if before.get("sett.performanceFeeGovernance") > 0 and valueGained:
            assert after.balances("sett", "treasury") > before.balances(
                "sett", "treasury"
            )

        ## Specific check to prove that gain was as modeled
        total_harvest_gain = after.get("sett.balance") - before.get("sett.balance")
        performance_fee_treasury = before.get("sett.performanceFeeGovernance")
        performance_fee_strategist = before.get("sett.performanceFeeStrategist")
        management_fee = before.get("sett.managementFee")
        time_since_last_harvest = after.get("sett.lastHarvestedAt") - before.get(
            "sett.lastHarvestedAt"
        )
        total_supply_before_deposit = before.get("sett.totalSupply")
        balance_before_deposit = before.get("sett.balance")

        fees = get_report_fees(
            total_harvest_gain,
            performance_fee_treasury,
            performance_fee_strategist,
            management_fee,
            time_since_last_harvest,
            total_supply_before_deposit,
            balance_before_deposit,
        )

        shares_perf_treasury = fees.shares_perf_treasury
        shares_management = fees.shares_management
        shares_perf_strategist = fees.shares_perf_strategist

        delta_strategist = after.balances("sett", "strategist") - before.balances(
            "sett", "strategist"
        )

        # assert delta_strategist == shares_perf_strategist
        # to void rounding error in large number calculation 
        assert approx(delta_strategist, shares_perf_strategist, 1)

        delta_treasury = after.balances("sett", "treasury") - before.balances(
            "sett", "treasury"
        )

        # assert delta_treasury == shares_perf_treasury + shares_management
        # to void rounding error in large number calculation  
        assert approx(delta_treasury, shares_perf_treasury + shares_management, 1)

        self.hook_after_harvest(before, after)
        

    def confirm_tend(self, before, after, tx):
        """
        Tend Should;
        - Increase the number of staked tended tokens in the strategy-specific mechanism
        - Reduce the number of tended tokens in the Strategy to zero

        (Strategy Must Implement)
        """
        assert False
