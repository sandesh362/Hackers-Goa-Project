// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/// @title FaceVerification - immutable timestamps for evidence-record digests.
contract FaceVerification {
    struct Record { bytes32 evidenceHash; address submitter; uint256 timestamp; }
    mapping(uint256 => Record) private records;
    uint256 public recordCount;

    event RecordStored(uint256 indexed id, bytes32 indexed evidenceHash, address indexed sender, uint256 timestamp);

    /// @notice Stores one SHA-256 digest of a canonical off-chain evidence record.
    function storeRecord(bytes32 evidenceHash) external returns (uint256 id) {
        id = recordCount++;
        records[id] = Record(evidenceHash, msg.sender, block.timestamp);
        emit RecordStored(id, evidenceHash, msg.sender, block.timestamp);
    }

    /// @notice Returns record metadata needed for independent verification.
    function getRecord(uint256 id) external view returns (bytes32, address, uint256) {
        Record memory record = records[id];
        return (record.evidenceHash, record.submitter, record.timestamp);
    }
}
