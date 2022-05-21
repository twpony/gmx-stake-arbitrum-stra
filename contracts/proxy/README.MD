## AdminUpgradeabilityProxy

Used for deployments so the contracts are upgradeable

## Security Notice

Most people can argue that the initialize function can be fronturn

In order to avoid that, deploy while calling the constructor on line 211, which also takes the initialization parameters.
This constructor will deploy the proxy and initialize it atomically, preventing any type of front-running