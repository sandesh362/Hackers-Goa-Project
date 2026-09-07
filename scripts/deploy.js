async function main() {
  const Factory = await ethers.getContractFactory("FaceVerification");
  const contract = await Factory.deploy();
  await contract.waitForDeployment();
  console.log(`CONTRACT_ADDRESS=${await contract.getAddress()}`);
}
main().catch((error) => { console.error(error); process.exitCode = 1; });
