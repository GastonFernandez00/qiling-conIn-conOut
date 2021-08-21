# https://etherscan.io/tx/0x9243d45ca81db4f16a0ded3e57982b4bc95ec32ce69d541bf6e019d949cbc6c8
# https://www.anquanke.com/post/id/145520

import sys

sys.path.append("../..")
from qiling import *


def example_run_evm():
    ql = Qiling(archtype="evm")
    contract = '0x606060405266017dfcdece4000600055341561001a57600080fd5b600160a060020a033316600090815260016020526040902066017dfcdece400090556106eb8061004b6000396000f3006060604052600436106100c45763ffffffff7c010000000000000000000000000000000000000000000000000000000060003504166306fdde0381146100c9578063095ea7b31461015357806318160ddd1461018957806323b872dd146101ae57806327edf097146101d6578063313ce567146101ff578063378dc3dc1461021257806342966c681461022557806370a082311461023b578063771282f61461025a57806395d89b411461026d578063a9059cbb14610280578063dd62ed3e146102a2575b600080fd5b34156100d457600080fd5b6100dc6102c7565b60405160208082528190810183818151815260200191508051906020019080838360005b83811015610118578082015183820152602001610100565b50505050905090810190601f1680156101455780820380516001836020036101000a031916815260200191505b509250505060405180910390f35b341561015e57600080fd5b610175600160a060020a03600435166024356102fe565b604051901515815260200160405180910390f35b341561019457600080fd5b61019c6103a4565b60405190815260200160405180910390f35b34156101b957600080fd5b610175600160a060020a03600435811690602435166044356103aa565b34156101e157600080fd5b6101e9610422565b60405160ff909116815260200160405180910390f35b341561020a57600080fd5b6101e9610427565b341561021d57600080fd5b61019c61042c565b341561023057600080fd5b610175600435610437565b341561024657600080fd5b61019c600160a060020a03600435166104ea565b341561026557600080fd5b61019c6104fc565b341561027857600080fd5b6100dc610502565b341561028b57600080fd5b610175600160a060020a0360043516602435610539565b34156102ad57600080fd5b61019c600160a060020a036004358116906024351661054f565b60408051908101604052600781527f48657861676f6e00000000000000000000000000000000000000000000000000602082015281565b60008115806103305750600160a060020a03338116600090815260026020908152604080832093871683529290522054155b151561033b57600080fd5b600160a060020a03338116600081815260026020908152604080832094881680845294909152908190208590557f8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b9259085905190815260200160405180910390a350600192915050565b60005490565b600160a060020a03808416600090815260026020908152604080832033909416835292905290812054829010156103e057600080fd5b600160a060020a038085166000908152600260209081526040808320339094168352929052208054839003905561041884848461056c565b5060019392505050565b600281565b600481565b66017dfcdece400081565b600160a060020a0333166000908152600160205260408120548290101561045d57600080fd5b600160a060020a033316600081815260016020526040808220805486900390558180527fa6eef7e35abe7026729641147f7915573c7e97b47efa546f5f6e3230263bcb4980548601905581548590039091557fcc16f5dbb4873280815c1ee09dbd06736cffcc184412cf7a71a0fdb75d397ca59084905190815260200160405180910390a2506001919050565b60016020526000908152604090205481565b60005481565b60408051908101604052600381527f4858470000000000000000000000000000000000000000000000000000000000602082015281565b600061054633848461056c565b50600192915050565b600260209081526000928352604080842090915290825290205481565b600160a060020a038216151561058157600080fd5b600160a060020a038316600090815260016020526040902054600282019010156105aa57600080fd5b600160a060020a038216600090815260016020526040902054818101116105d057600080fd5b600160a060020a03808416600081815260016020526040808220805460011990879003810190915593861682528082208054860190558180527fa6eef7e35abe7026729641147f7915573c7e97b47efa546f5f6e3230263bcb4980546002908101909155825490940190915590917fcc16f5dbb4873280815c1ee09dbd06736cffcc184412cf7a71a0fdb75d397ca5915160ff909116815260200160405180910390a281600160a060020a031683600160a060020a03167fddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef8360405190815260200160405180910390a35050505600a165627a7a72305820fbef5b10322242b8659b5de8e24ec1cf5e809831f6f7c08e52112f76daa31aef0029'

    user1 = ql.arch.evm.create_account(balance=100*10**18)
    user2 = ql.arch.evm.create_account(balance=100*10**18)
    c1 = ql.arch.evm.create_account()

    def check_balance(sender, destination):
        call_data = '0x70a08231'+ql.arch.evm.abi.convert(['address'], [sender])
        msg2 = ql.arch.evm.create_message(sender, destination, data=call_data)
        return ql.run(code=msg2)

    # Deploy runtime code
    msg0 = ql.arch.evm.create_message(user1, b'', code=contract, contract_address=c1)
    ql.run(code=msg0)

    # # SMART CONTRACT DEPENDENT: check balance of user1
    result = check_balance(user1, c1)
    print('User1 balance =', int(result.output.hex()[2:], 16))

    # # SMART CONTRACT DEPENDENT: transform from user1 to user2
    call_data = '0xa9059cbb'+ ql.arch.evm.abi.convert(['address'], [user2]) + \
                                    ql.arch.evm.abi.convert(['uint256'], [0xfffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffe])
    msg1 = ql.arch.evm.create_message(user1, c1, data=call_data)    
    result = ql.run(code=msg1)
    if int(result.output.hex()[2:], 16) ==  1:
        print('User1 transfered Token to User1')

    # # SMART CONTRACT DEPENDENT: User1 balance underflow, MAX - 1
    result = check_balance(user1, c1)
    print('User1 final balance =', int(result.output.hex()[2:], 16))

    result = check_balance(user2, c1)
    print('User2 final balance =', int(result.output.hex()[2:], 16))

if __name__ == "__main__":
    example_run_evm()