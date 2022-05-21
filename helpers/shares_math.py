from dotmap import DotMap
"""
  Set of functions to calculate shares burned, fees, and want withdrawn or deposited
"""

MAX_BPS = 10_000
SECS_PER_YEAR = 31_556_952

def from_want_to_shares(
    want_deposited, total_supply_before_deposit, balance_before_deposit
):
    """
    Used to estimate how many shares you'll get for a deposit
    """
    ## Math from Soldity
    expected_shares = (
        want_deposited * total_supply_before_deposit // balance_before_deposit
    )

    return expected_shares


def from_shares_to_want(
    shares_to_burn, ppfs_before_withdraw, vault_decimals
):
    """
    Used to estimate how much want you'll get for a withdrawal, by burning the shares (including fees)
    """
    ## Math from Solidity
    expected_want = shares_to_burn * ppfs_before_withdraw // 10 ** vault_decimals

    return expected_want


def get_withdrawal_fees_in_want(
    shares_to_burn, ppfs_before_withdraw, vault_decimals, withdrawal_fee_bps
):
    """
    Used to calculate the fees (in want) the treasury will receive when taking withdrawal fees
    """
    ## Math from Solidity
    value = shares_to_burn * ppfs_before_withdraw // 10 ** vault_decimals
    fees = value * withdrawal_fee_bps // MAX_BPS

    return fees


def get_withdrawal_fees_in_shares(
    shares_to_burn,
    ppfs_before_withdraw,
    vault_decimals,
    withdrawal_fee_bps,
    total_supply_before_withdraw,
    vault_balance_before_withdraw,
):
    """
    Used to calculate the shares that will be issued for treasury when taking withdrawal fee during a withdrwal
    """
    ## More rigorously: We had an increase in shares equal to depositing the fees
    expected_fee_in_want = get_withdrawal_fees_in_want(
        shares_to_burn, ppfs_before_withdraw, vault_decimals, withdrawal_fee_bps
    )

    ## Math from code ## Issues shares based on want * supply / balance
    expected_shares = (
        expected_fee_in_want
        * total_supply_before_withdraw
        // vault_balance_before_withdraw
    )
    return expected_shares


def get_performance_fees_want(total_harvest_gain, performance_fee):
    """
    Given the harvested Want returns the fee in want
    """

    return total_harvest_gain * performance_fee // MAX_BPS

def get_management_fees_want(total_assets, time_passed, management_fee):
    """
    Given the total assets, the time expired and the management fee, returns the management fee in want
    """

    return management_fee  * total_assets * time_passed // SECS_PER_YEAR // MAX_BPS


def get_performance_fees_shares(
    total_harvest_gain,
    performance_fee,
    total_supply_before_deposit,
    balance_before_deposit,
):
    """
    Given the harvested Want, and the vault state before the harvest
    Returns the amount of shares that will be issued for that performance fee
    """

    fee_in_want = get_performance_fees_want(total_harvest_gain, performance_fee)

    ## TODO: Add Performance Fee Governance
    ## TODO: Add Performance Fee Strategist
    ## TODO: Add Management Fee

    ## Given the fee, and the total gains
    ## Estimate the growth of the pool by that size

    ## At harvest, supply of shares is not increased
    new_total_supply = total_supply_before_deposit
    ## New balance will be  balance_before_deposit + total_harvest_gain, subtract fee_in_want to avoid double counting
    balance_at_harvest = (
        balance_before_deposit + total_harvest_gain - fee_in_want * 2
    )  ## NOTE: Assumes the fees are 50/50

    return from_want_to_shares(fee_in_want, new_total_supply, balance_at_harvest)


def get_report_fees(
    total_harvest_gain,
    performance_fee_treasury,
    performance_fee_strategist,
    management_fee,
    time_since_last_harvest,
    total_supply_before_deposit,
    balance_before_deposit,
):
    """
        Given the harvest info, and vault settings
        Returns the amount of shares issues for:
        Perf fee to treasury
        Management fee to treasury
        Perf fee to Strategist
    """

    ## Change so that
    ## 1. Calculate fees in wants
    ## 2. Get pool amount changes based on 1
    ## 3. Actually issue shares
    balance = balance_before_deposit + total_harvest_gain
    new_total_supply = total_supply_before_deposit

    fee_in_want_treasury = get_performance_fees_want(total_harvest_gain, performance_fee_treasury)
    management_fee_in_want = get_management_fees_want(balance_before_deposit, time_since_last_harvest, management_fee)
    fee_in_want_strategist = get_performance_fees_want(total_harvest_gain, performance_fee_strategist)

    ## Get the shares
    pool = balance - fee_in_want_treasury - management_fee_in_want - fee_in_want_strategist
    shares_perf_treasury = from_want_to_shares(fee_in_want_treasury, new_total_supply, pool)
    new_total_supply += shares_perf_treasury
    pool = pool + fee_in_want_treasury

    shares_management = from_want_to_shares(management_fee_in_want, new_total_supply, pool)
    new_total_supply += shares_management
    pool = pool + management_fee_in_want

    shares_perf_strategist = from_want_to_shares(fee_in_want_strategist, new_total_supply, pool)


    return DotMap(
        shares_perf_treasury=shares_perf_treasury,
        shares_management=shares_management,
        shares_perf_strategist=shares_perf_strategist,
    )
