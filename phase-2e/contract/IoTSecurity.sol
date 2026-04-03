pragma solidity ^0.8.0;

contract IoTSecurity {

    struct Attack {
        string ip;
        string attackType;
        string dataHash;
        uint timestamp;
    }

    Attack[] public attacks;

    function logAttack(
        string memory _ip,
        string memory _type,
        string memory _hash
    ) public {
        attacks.push(Attack(_ip, _type, _hash, block.timestamp));
    }
}