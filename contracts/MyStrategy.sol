// SPDX-License-Identifier: MIT

pragma solidity 0.6.12;
pragma experimental ABIEncoderV2;

import {BaseStrategy} from "@badger-finance/BaseStrategy.sol";

import {ISwapRouter} from "../interfaces/ISwapRouter.sol";
import {IRewardRouterV2} from "../interfaces/IRewardRouterV2.sol";
import {IRewardTracker} from "../interfaces/IRewardTracker.sol";
import {IVester} from "../interfaces/IVester.sol";
import {IVault} from "../interfaces/IVault.sol";
import "@openzeppelin-contracts-upgradeable/token/ERC20/IERC20Upgradeable.sol";
import "@uniswap/interfaces/IUniswapV3Factory.sol";
import "./libraries/OracleLibrary.sol";
import "./libraries/TransferHelper.sol";

contract MyStrategy is BaseStrategy {
    address public constant BADGER = 0x3472A5A71965499acd81997a54BBA8D852C6E53d;
    address public constant WETH = 0x82aF49447D8a07e3bd95BD0d56f35241523fBab1;

    address public constant GMX = 0xfc5A1A6EB076a2C7aD06eD22C90d7E710E35ad0a;
    address public constant ESGMX = 0xf42Ae1D54fd613C9bb14810b0588FaAa09a426cA;
    address public constant BNGMX = 0x35247165119B69A40edD5304969560D0ef486921;

    address public constant stakedGmxTracker = 0x908C4D94D34924765f1eDc22A1DD098397c59dD4;
    address public constant bonusGmxTracker = 0x4d268a7d4C16ceB5a606c173Bd974984343fea13;
    address public constant feeGmxTracker = 0xd2D1162512F927a7e282Ef43a362659E4F2a728F;

    address public constant GmxVester = 0x199070DDfd1CFb69173aa2F7e20906F26B363004;

    address public constant RewardRouterV2 = 0xA906F338CB21815cBc4Bc87ace9e68c87eF8d8F1;
    address public constant UniswapV3Router = 0xE592427A0AEce92De3Edee1F18E0157C05861564;
    address public constant UniswapV3factory = 0x1F98431c8aD98523631AE4a59f267346ea31F984;
    address public WethGmxPool;

    uint24 public swapPoolFee;
    uint32 public twapInterval;
    uint256 public slipRange;

    /**
        @dev Initialize the Strategy with security settings as well as tokens
        @param _vault: vault address
        @param _wantConfig: want token address
    */
    function initialize(address _vault, address[1] memory _wantConfig) public initializer {
        __BaseStrategy_init(_vault);

        want = _wantConfig[0];

        // swap params
        swapPoolFee = 10000; // 1.0%
        twapInterval = 600; // 10 minutes
        slipRange = 300; // 3.0%

        // Approve for GMX stake and ESGMX Vest
        IERC20Upgradeable(GMX).approve(stakedGmxTracker, type(uint256).max);
        IERC20Upgradeable(ESGMX).approve(stakedGmxTracker, type(uint256).max);

        IERC20Upgradeable(stakedGmxTracker).approve(bonusGmxTracker, type(uint256).max);

        IERC20Upgradeable(bonusGmxTracker).approve(feeGmxTracker, type(uint256).max);
        IERC20Upgradeable(BNGMX).approve(feeGmxTracker, type(uint256).max);

        getPoolAddr();
    }

    /**
        @dev Return the name of the strategy
    */
    function getName() external pure override returns (string memory) {
        return "Strategy-GMX";
    }

    /**
        @dev Return a list of protected tokens
        @notice It's very important all tokens that are meant to be in the strategy to be marked as protected
                this provides security guarantees to the depositors they can't be sweeped away
    */
    function getProtectedTokens() public view virtual override returns (address[] memory) {
        address[] memory protectedTokens = new address[](6);
        protectedTokens[0] = want;
        protectedTokens[1] = BADGER;
        protectedTokens[2] = ESGMX;
        protectedTokens[3] = BNGMX;
        protectedTokens[4] = WETH;
        return protectedTokens;
    }

    /**
        @dev Deposit `_amount` of want, investing it to earn yield
        @param _amount: the amount of want(GMX) 
        @notice stake the swap GMX by RewardRouterV2     
    */
    function _deposit(uint256 _amount) internal override {
        // stake GMX
        stakeGmx(_amount);
    }

    /**
        @dev stake GMX by RewardRouterV2
        @param _amount: the amount of GMX to stake     
    */
    function stakeGmx(uint256 _amount) public {
        _ActorsCheck();
        if (_amount == 0) {
            return;
        }
        uint256 _balance = IERC20Upgradeable(GMX).balanceOf(address(this));
        if (_balance < _amount) {
            _amount = _balance;
        }
        IRewardRouterV2(RewardRouterV2).stakeGmx(_amount);
    }

    /**
        @dev unstake GMX by RewardRouterV2
        @param _amount: the amount of GMX to unstake     
    */
    function unstakeGmx(uint256 _amount) public {
        _ActorsCheck();
        if (_amount == 0) {
            return;
        }
        // to check _amount not more than staked amount in feeGmxTracker
        uint256 _GmxBalance = IRewardTracker(stakedGmxTracker).depositBalances(address(this), GMX);
        if (_GmxBalance < _amount) {
            _amount = _GmxBalance;
        }

        // to check _amount not more than feeGmxTracker.balanceof(account)
        // if deposit in GMXVester, feeGmxTracker.balanceof(account) will be transferred to GMXVester
        uint256 _feeGmxTrackerBalance = IRewardTracker(feeGmxTracker).balanceOf(address(this));
        if (_feeGmxTrackerBalance < _amount) {
            _amount = _feeGmxTrackerBalance;
        }

        IRewardRouterV2(RewardRouterV2).unstakeGmx(_amount);
    }

    /**
        @dev vest ESGMX in GMXVester
        @param _amount the amount of ESGMX to vest     
    */
    function vestEsGmx(uint256 _amount) public {
        _ActorsCheck();
        if (_amount == 0) {
            return;
        }
        uint256 _balance = IERC20Upgradeable(ESGMX).balanceOf(address(this));
        if (_balance < _amount) {
            _amount = _balance;
        }

        IERC20Upgradeable(ESGMX).approve(GmxVester, _amount);
        IERC20Upgradeable(feeGmxTracker).approve(GmxVester, type(uint256).max);

        IVester(GmxVester).deposit(_amount);
    }

    /**
        @dev unvest ESGMX in GMXVester
        @notice unvest ESGMX must withdraw all ESGMX in GMXVester    
    */
    function unvestEsGmx() public {
        _ActorsCheck();
        if ((IVester(GmxVester).balances(address(this))) > 0) {
            IVester(GmxVester).withdraw();
        }
    }

    /**
        @dev single swap by Uniswap V3 Router
        @param _tokenIn: the input token address
        @param _tokenOut: the output token address
        @param _swapFee: the swap fee
        @param _amountIn: the amount to swap
        @param _amountOutMinimum the minimum swap out amount
        @param _amountOut: the amount of want needed
        @param _amountInMaximum: the maximum amountIn in output single mode
    */
    function _singleSwap(
        address _tokenIn,
        address _tokenOut,
        uint24 _swapFee,
        uint256 _amountIn,
        uint256 _amountOutMinimum,
        uint256 _amountOut,
        uint256 _amountInMaximum
    ) internal returns (uint256 _output) {
        if (_amountIn == 0 && _amountOut == 0) {
            return 0;
        }

        if (_amountIn > 0) {
            TransferHelper.safeApprove(_tokenIn, UniswapV3Router, _amountIn);
            ISwapRouter.ExactInputSingleParams memory params = ISwapRouter.ExactInputSingleParams({
                tokenIn: _tokenIn,
                tokenOut: _tokenOut,
                fee: _swapFee,
                recipient: address(this),
                deadline: block.timestamp,
                amountIn: _amountIn,
                amountOutMinimum: _amountOutMinimum,
                sqrtPriceLimitX96: 0
            });
            _output = ISwapRouter(UniswapV3Router).exactInputSingle(params);
            return _output;
        } else {
            TransferHelper.safeApprove(_tokenIn, UniswapV3Router, _amountInMaximum);
            ISwapRouter.ExactOutputSingleParams memory params = ISwapRouter.ExactOutputSingleParams({
                tokenIn: _tokenIn,
                tokenOut: _tokenOut,
                fee: _swapFee,
                recipient: address(this),
                deadline: block.timestamp,
                amountOut: _amountOut,
                amountInMaximum: _amountInMaximum,
                sqrtPriceLimitX96: 0
            });
            _output = ISwapRouter(UniswapV3Router).exactOutputSingle(params);
            return _output;
        }
    }

    /**
        @dev Estimate Amount Out from Uniswap V3 Pool Oracle
        @param tokenIn the tokenIn address
        @param tokenOut the tokenOut address
        @param amountIn the tokenIn amount
        @param secondsAgo the tick interval
        @param pool     the swap pool address
        @return amountOut the tokenOut amount
    */
    function estimateAmountOut(
        address tokenIn,
        address tokenOut,
        uint256 amountIn,
        uint32 secondsAgo,
        address pool
    ) internal view returns (uint256 amountOut) {
        uint32[] memory secondsAgos = new uint32[](2);
        secondsAgos[0] = secondsAgo;
        secondsAgos[1] = 0;

        (int56[] memory tickCumulatives, ) = IUniswapV3Pool(pool).observe(secondsAgos);

        int56 tickCumulativesDelta = tickCumulatives[1] - tickCumulatives[0];

        int24 tick = int24(tickCumulativesDelta / secondsAgo);

        if (tickCumulativesDelta < 0 && (tickCumulativesDelta % secondsAgo != 0)) {
            tick--;
        }

        uint128 amountIn128 = uint128(amountIn);
        require(amountIn == uint256(amountIn128), "AmounInError");

        amountOut = OracleLibrary.getQuoteAtTick(tick, amountIn128, tokenIn, tokenOut);
    }

    /**
        @dev Estimate WETH in GMX
        @param amountIn  the amount of WETH
        @return amountOut  the amount of GMX
    */
    function getWETHinGMX(uint256 amountIn, uint32 secondsAgo) public view returns (uint256 amountOut) {
        if (amountIn == 0) {
            return 0;
        }
        amountOut = estimateAmountOut(WETH, GMX, amountIn, secondsAgo, WethGmxPool);
        return amountOut;
    }

    /**
        @dev withdraw All non-locked fund
        @notice withdraw steps:
                1. unVest ESGmx
                2. unstake GMX
                3. swap WETH to GMX
    */
    function _withdrawAll() internal override {
        // unVest EsGmx
        unvestEsGmx();

        // unstake GMX
        uint256 _gmxUnstake = IRewardTracker(stakedGmxTracker).depositBalances(address(this), GMX);
        unstakeGmx(_gmxUnstake);

        uint256 _gmxBalance = IERC20Upgradeable(want).balanceOf(address(this));
        uint256 _wethBalance = IERC20Upgradeable(WETH).balanceOf(address(this));

        // transfer WETH
        uint256 _minOut = (getWETHinGMX(_wethBalance, twapInterval)).mul(MAX_BPS.sub(slipRange)).div(MAX_BPS);
        uint256 _swapAmount = _singleSwap(WETH, want, swapPoolFee, _wethBalance, _minOut, 0, 0);
    }

    /**
        @dev Withdraw _amount of want, it can be sent to the vault / depositor
        @param _amount: the amount of want to withdraw
        @notice withdraw steps:
                1. withdraw WETH;
                2. unVest GMXVester, withdraw GMX; (if step 2 not enough)
                3. unstake GMX in stakedGMXTrakcer, withdraw GMX; (if step 2 and 3 not enough)
                4. otherwise, unstake all GMX in stakedGMXTrakcer
    */
    function _withdrawSome(uint256 _amount) internal override returns (uint256) {
        // to swap ETH to GMX
        uint256 _wethBalance = IERC20Upgradeable(WETH).balanceOf(address(this));
        uint256 _wethInGMX = getWETHinGMX(_wethBalance, twapInterval);
        uint256 _minOut = _wethInGMX.mul(MAX_BPS.sub(slipRange)).div(MAX_BPS);
        uint256 _swapAmount = _singleSwap(WETH, want, swapPoolFee, _wethBalance, _minOut, 0, 0);

        uint256 _wantBalance = IERC20Upgradeable(want).balanceOf(address(this));

        if (_amount < _wantBalance) {
            return _amount;
        }

        // WETH and left GMX is not enough, unvest GMXVester
        unvestEsGmx();

        uint256 _gmxStaked = IRewardTracker(stakedGmxTracker).depositBalances(address(this), GMX);
        uint256 _gmxUnstake;

        // calculate the amount to unstake
        if (_amount < _wantBalance.add(_gmxStaked)) {
            _gmxUnstake = _amount.sub(_wantBalance);
        } else {
            _gmxUnstake = _gmxStaked;
        }

        unstakeGmx(_gmxUnstake);
        uint256 _wantBalanceAfter = IERC20Upgradeable(want).balanceOf(address(this));

        return _wantBalanceAfter.sub(_wantBalance);
    }

    /**
        @dev the strategy can ben tended
    */
    function _isTendable() internal pure override returns (bool) {
        return true; // Change to true if the strategy should be tended
    }

    /**
        @dev Harvest the reward token
        @dev Just harvest the reward, not stake GMX or vest ESGMX again
        @dev If you wanna stake GMX or vest ESGMX, you can call tend()
        @return harvested to record the harvested token and amount
        @notice There are 3 reward tokens from Tracker: WETH, ESGMX, BNGMX
        @notice Actions for 3 rewards:
                1) WETH from feeGmxTracker -> a) No Action, just deposit WETH.
                2) ESGMX from stakedGmxTracker -> a) Vest in GmxVester to get GMX
                3) BNGMX from bonusGmxTracker -> a) Staked to get WETH; b) No Action, just deposit WETH;
                ESGMX cannot be transfered, must vest in GmxVester to get GMX. To claim the GMX from GMXVester:
                1) GMX from GmxVester -> a) Stake GMX again
    */
    function _harvest() internal override returns (TokenAmount[] memory harvested) {
        uint256 _poolBefore = balanceOfPool();
        uint256 _vaultBefore = IVault(vault).balance();

        harvested = new TokenAmount[](3);

        harvested[0] = TokenAmount(WETH, 0);
        harvested[1] = TokenAmount(ESGMX, 0);
        harvested[2] = TokenAmount(GMX, 0);

        uint256 _wethBefore = IERC20Upgradeable(WETH).balanceOf(address(this));
        uint256 _esGMXBefore = IERC20Upgradeable(ESGMX).balanceOf(address(this));
        uint256 _GMXBefore = IERC20Upgradeable(GMX).balanceOf(address(this));

        IRewardRouterV2(RewardRouterV2).handleRewards(true, false, true, false, true, true, false);

        uint256 _wethAfter = IERC20Upgradeable(WETH).balanceOf(address(this));
        uint256 _esGMXAfter = IERC20Upgradeable(ESGMX).balanceOf(address(this));
        uint256 _GMXAfter = IERC20Upgradeable(GMX).balanceOf(address(this));

        harvested[0].amount = _wethAfter.sub(_wethBefore);
        harvested[1].amount = _esGMXAfter.sub(_esGMXBefore);
        harvested[2].amount = _GMXAfter.sub(_GMXBefore);

        // ESGMX cannot be transferred, and must vest in GmxVester to become GMX
        // So here we just to report WETH and GMX amount
        uint256 _wethInWant = getWETHinGMX(harvested[0].amount, twapInterval);

        _reportToVault(_wethInWant.add(harvested[2].amount));

        // if you wanna stake GMX in sGMXTracker and vest ESGMX in GMXVester
        // you can tend

        return harvested;
    }

    /**
        @dev stake the left GMX; vest the left ESGMX
        @return  tended  the amount of tokens to tend
        @notice  tended[0]: the amount of want to deposit and stake
                 tended[1]: the amount of ESGMX to vest in GMXVester
    */
    function _tend() internal override returns (TokenAmount[] memory tended) {
        tended = new TokenAmount[](2);
        tended[0] = TokenAmount(want, 0);
        tended[1] = TokenAmount(ESGMX, 0);

        uint256 _wantBalance = IERC20Upgradeable(want).balanceOf(address(this));
        uint256 _esGMXBalance = IERC20Upgradeable(ESGMX).balanceOf(address(this));

        // stake GMX in sGMXTracker
        if (_wantBalance > 0) {
            tended[0].amount = _wantBalance;
            _deposit(_wantBalance);
        }

        if (_esGMXBalance == 0) {
            return tended;
        }
        // vest ESGMX in GMXVester
        // vest ESGMX need to have GMX staked
        uint256 _pairAmount = IVester(GmxVester).pairAmounts(address(this));
        uint256 _pairbalance = IVester(GmxVester).balances(address(this));
        _pairbalance = _pairbalance.add(_esGMXBalance);
        uint256 _nextpairAmount = IVester(GmxVester).getPairAmount(address(this), _pairbalance);

        if (_nextpairAmount <= _pairAmount) {
            tended[1].amount = _esGMXBalance;
            vestEsGmx(_esGMXBalance);
        } else {
            uint256 _pairAmountDiff = _nextpairAmount.sub(_pairAmount);
            uint256 a = IERC20Upgradeable(feeGmxTracker).balanceOf(address(this));
            if (a >= _pairAmountDiff) {
                tended[1].amount = _esGMXBalance;
                vestEsGmx(_esGMXBalance);
            }
        }

        return tended;
    }

    /**
        @dev Return the balance of Pool; Asset can be swapped to want immediately. 
        @return _amountPool the pool balance can be swapped to want
        @notice balance of pool includes 2 parts:
                1. staked GMX in stakedGmxTracker
                2. WETH balance (the realized reward)
    */
    function balanceOfPool() public view override returns (uint256 _amountPool) {
        // staked amount in stakedGmxTracker
        uint256 _poolBalance = IRewardTracker(stakedGmxTracker).depositBalances(address(this), GMX);

        // WETH balance
        uint256 _wethBalance = IERC20Upgradeable(WETH).balanceOf(address(this));

        // to quote weth balance in want
        uint256 _wethInWant = getWETHinGMX(_wethBalance, twapInterval);

        _amountPool = _poolBalance.add(_wethInWant);
        return _amountPool;
    }

    /**
        @dev Return the reward balance and the claimable reward 
        @notice Used for offChain APY and Harvest Health monitoring
        @notice To track the ESGMX and WETH 
    */
    function balanceOfRewards() public view override returns (TokenAmount[] memory rewards) {
        // Rewards are 0
        rewards = new TokenAmount[](2);

        rewards[0] = TokenAmount(WETH, 0);
        rewards[1] = TokenAmount(ESGMX, 0);

        rewards[0].amount = _getWethRewardAmount();
        rewards[1].amount = _getEsGmxRewardAmount();

        return rewards;
    }

    /**
        @dev Return the Weth balance and the claimable Weth reward
        @return _amount the amount of Weth and claimable Weth
        @notice WETH rewards have 3 parts:
        @notice 1. WETH balance;
                2. the claimable WETH reward from feeGmxTracker;
                3. the claimable BNGMX from bonusGmxTracker may lead to the claimable WETH from feeGmxTracker
    */
    function _getWethRewardAmount() internal view returns (uint256 _amount) {
        uint256 _wethBalance = IERC20Upgradeable(WETH).balanceOf(address(this));
        uint256 _wethClaimable = IRewardTracker(feeGmxTracker).claimable(address(this));

        uint256 _wethClaimableWithoutPending = IRewardTracker(feeGmxTracker).claimableReward(address(this));
        uint256 _stakedAmount = IRewardTracker(feeGmxTracker).stakedAmounts(address(this));

        // to calculate the amount of WETH which can be transformed by claimable BNGMX
        uint256 _bnGMXBalance = IERC20Upgradeable(BNGMX).balanceOf(address(this));
        uint256 _claimableBnGMX = IRewardTracker(bonusGmxTracker).claimable(address(this));

        _amount = (_wethClaimable.sub(_wethClaimableWithoutPending)).mul(_bnGMXBalance.add(_claimableBnGMX)).div(_stakedAmount);
        _amount = _amount.add(_wethBalance).add(_wethClaimable);
        return _amount;
    }

    /**
        @dev Return the EsGmx balance and the claimable EsGmx reward
        @return _amount the amount of EsGmx and claimable EsGmx
        @notice the claimable ESGMX has 4 parts:
        @notice 1. the ESGMX balance
                2. staked ESGMX in stakedGmxTracker( zero in this strategy)
                3. vested ESGMX in GmxVester
                4. the claimable ESGMX reward from stakedGmxTracker
    */
    function _getEsGmxRewardAmount() internal view returns (uint256 _amount) {
        uint256 _esGmxBalance = IERC20Upgradeable(ESGMX).balanceOf(address(this));
        // in this strategy, not stake ESGMX, so this amount is 0
        uint256 _esGmxStakedInSGmxTracker = IRewardTracker(stakedGmxTracker).depositBalances(address(this), ESGMX);

        uint256 _esGmxInGmxVester = IVester(GmxVester).balances(address(this));
        uint256 _esGmxClaimable = IRewardTracker(stakedGmxTracker).claimable(address(this));

        _amount = _esGmxBalance.add(_esGmxStakedInSGmxTracker).add(_esGmxInGmxVester).add(_esGmxClaimable);
        return _amount;
    }

    /**
        @dev set the two steps swap pool fee
        @notice swapPoolFee:  wbtc <-> weth
                TWAP interval in seconds
     */
    function setSwapParams(
        uint24 _swapFee,
        uint32 _interval,
        uint256 _range
    ) external {
        _onlyAuthorizedActors();
        swapPoolFee = _swapFee;
        twapInterval = _interval;
        slipRange = _range;
    }

    /**
        @dev Set the Uniswap V3 Pool Address
        @notice WETH <-> GMX
    */
    function getPoolAddr() public {
        _ActorsCheck();
        WethGmxPool = IUniswapV3Factory(UniswapV3factory).getPool(WETH, GMX, swapPoolFee);
        require(WethGmxPool != address(0), "WethGmxPool doesn't exist");
    }

    /**
        @dev For functions that only known entities should call
        @notice Checks whether a call is from vault or governance or keeper.
    */
    function _ActorsCheck() internal view {
        require(msg.sender == vault || msg.sender == governance() || msg.sender == keeper(), "only Authorized Actors");
    }
}
