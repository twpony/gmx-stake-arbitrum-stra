// SPDX-License-Identifier: MIT

pragma solidity 0.6.12;
pragma experimental ABIEncoderV2;

import {TestVipCappedGuestListBbtcUpgradeable} from "@badger-finance/test/TestVipCappedGuestListBbtcUpgradeable.sol";

contract TheGuestlist is TestVipCappedGuestListBbtcUpgradeable {
  // So Brownie compiles it tbh
  // Changes here invalidate the bytecode, breaking trust of the mix
  // DO NOT CHANGE THIS FILE
}