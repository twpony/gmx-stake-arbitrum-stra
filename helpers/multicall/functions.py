from dotmap import DotMap


def as_wei(value):
    return value


def as_original(value):
    return value


erc20 = DotMap(
    balanceOf="balanceOf(address)(uint256)",
    totalSupply="totalSupply()(uint256)",
    transfer="transfer(address,uint256)()",
    safeTransfer="safeTransfer(address,uint256)()",
    name="name()(string)",
    symbol="symbol()(string)",
    decimals="decimals()(uint256)",
)
sett = DotMap(
    getPricePerFullShare="getPricePerFullShare()(uint256)",
    available="available()(uint256)",
    balance="balance()(uint256)",
    controller="controller()(address)",
    governance="governance()(address)",
    strategist="strategist()(address)",
    keeper="keeper()(address)",
    shares="shares()(uint256)",
    managementFee="managementFee()(uint256)",
    withdrawalFee="withdrawalFee()(uint256)",
    lastHarvestedAt="lastHarvestedAt()(uint256)",
    performanceFeeGovernance="performanceFeeGovernance()(uint256)",
    performanceFeeStrategist="performanceFeeStrategist()(uint256)",
)
strategy = DotMap(
    balanceOfPool="balanceOfPool()(uint256)",
    balanceOfWant="balanceOfWant()(uint256)",
    balanceOf="balanceOf()(uint256)",
    isTendable="isTendable()(bool)",
    getProtectedTokens="getProtectedTokens()(address[])",
    getName="getName()(string)",
    farmPerformanceFeeGovernance="farmPerformanceFeeGovernance()(uint256)",
    farmPerformanceFeeStrategist="farmPerformanceFeeStrategist()(uint256)",
    sharesOfPool="sharesOfPool()(uint256)",
    sharesOfWant="sharesOfWant()(uint256)",
    sharesOf="sharesOf()(uint256)",
)

stakedGmxTracker = DotMap(
    depositBalances="depositBalances(address,address)(uint256)",
)


harvestFarm = DotMap(earned="earned()(uint256)")
rewardPool = DotMap(
    # claimable rewards
    earned="earned(address)(uint256)",
    # amount staked
    balanceOf="balanceOf(address)(uint256)",
)
digg = DotMap(sharesOf="sharesOf(address)(uint256)")
diggFaucet = DotMap(
    # claimable rewards
    earned="earned()(uint256)",
)
pancakeChef = DotMap(
    pendingCake="pendingCake(uint256,uint256)(uint256)",
    userInfo="userInfo(uint256,address)(uint256,uint256)",
)

func = DotMap(
    erc20=erc20,
    sett=sett,
    strategy=strategy,
    rewardPool=rewardPool,
    diggFaucet=diggFaucet,
    digg=digg,
    pancakeChef=pancakeChef,
    stakedGmxTracker=stakedGmxTracker,
)
