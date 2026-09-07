require("@nomicfoundation/hardhat-toolbox");
require("dotenv").config();

module.exports = {
  solidity: "0.8.24",
  networks: {
    localhost: { url: "http://127.0.0.1:8545" },
    amoy: { url: process.env.WEB3_RPC_URL || "https://rpc-amoy.polygon.technology", accounts: process.env.PRIVATE_KEY ? [process.env.PRIVATE_KEY] : [] }
  }
};
