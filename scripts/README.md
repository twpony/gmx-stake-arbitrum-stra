# Scripts

These are a set of scripts BadgerDAO developers use to get a Vault and Strategy into production

## 1_production_deploy.py

Deploy the logic and proxies for Vault and Strategy
Give the deployer governance

NOTE: The deployed contracts are NOT SAFE until governance is handed to timelock

## 2_production_guestlist.py

Deploy and setup the guestlist for the given vault
Make sure to change the parameters to make this work

## 3_production_setup.py

Setup all the parameters to production by using the BadgerRegistry to fetch safe defaults.

NOTE: After this stage the Vault and Strategy MAYBE safe. You have to verify the settings to ensure they are properly set to safe values.


## TODO: 4. 5. 6 if they are even needed