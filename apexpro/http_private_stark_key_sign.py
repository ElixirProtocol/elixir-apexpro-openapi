import decimal
import decimal
import math

from apexpro.constants import URL_SUFFIX, ORDER_SIDE_BUY
from apexpro.helpers.request_helpers import random_client_id, iso_to_epoch_seconds, epoch_seconds_to_iso
from apexpro.http_private import HttpPrivate
from apexpro.starkex.conditional_transfer import SignableConditionalTransfer
from apexpro.starkex.constants import ONE_HOUR_IN_SECONDS, ORDER_SIGNATURE_EXPIRATION_BUFFER_HOURS
from apexpro.starkex.helpers import get_transfer_erc20_fact, nonce_from_client_id
from apexpro.starkex.order import SignableOrder, DECIMAL_CONTEXT_ROUND_UP, DECIMAL_CONTEXT_ROUND_DOWN
from apexpro.starkex.transfer import SignableTransfer
from apexpro.starkex.withdrawal import SignableWithdrawal


class HttpPrivateStark(HttpPrivate):
    def create_order(self,
                     symbol,
                     side,
                     type,
                     size,
                     limitFee,
                     price=None,
                     accountId=None,
                     timeInForce="GOOD_TIL_CANCEL",
                     reduceOnly=False,
                     triggerPrice=None,
                     trailingPercent=None,
                     clientId=None,
                     expiration=None,
                     expirationEpochSeconds=None,
                     signature=None, ):
        """"
        POST  create_order.
        client.create_order(symbol="BTC-USDC", side="SELL",
                                           type="LIMIT", size="0.01",
                                           price="20000", limitFee="1",
                                            accountId="325881046451093849",reduceOnly=False,
                                           expiration=now_iso + SEVEN_DAYS_S + 60*1000, timeInForce="GOOD_TIL_CANCEL")

       :returns: Request results as dictionary.
       """

        clientId = clientId or random_client_id()
        if not self.stark_private_key:
            raise Exception(
                'No signature provided and client was not ' +
                'initialized with stark_private_key'
            )

        if bool(expiration) == bool(expirationEpochSeconds):
            raise ValueError(
                'Exactly one of expiration and expiration_epoch_seconds must '
                'be specified',
            )
        expiration = expiration or epoch_seconds_to_iso(
            expirationEpochSeconds,
        )
        expirationEpochSeconds = (
                expirationEpochSeconds or iso_to_epoch_seconds(expiration)
        )

        accountId = accountId or self.account['positionId']
        if not accountId:
            raise Exception(
                'No accountId provided' +
                'please call account()'
            )

        if not self.config:
            raise Exception(
                'No config provided' +
                'please call configs()'
            )
        symbolData = {}
        currency = {}
        for k, v in enumerate(self.config['perpetualContract']):
            if v['symbol'] == symbol:
                symbolData = v
        for k, v2 in enumerate(self.config['currency']):
            if v2['id'] == symbolData['settleCurrencyId']:
                currency = v2

        if symbolData is not None :
            number = float(price)/float(symbolData.get('tickSize'))
            if number > float(int(number)):
                raise Exception(
                    'the price must Multiple of tickSize'
                )

        order_to_sign = SignableOrder(
            position_id=accountId,
            client_id=clientId,
            market=symbol,
            side=side,
            human_size=size,
            human_price=price,
            limit_fee=limitFee,
            expiration_epoch_seconds=expirationEpochSeconds,
            synthetic_resolution=symbolData['starkExResolution'],
            synthetic_id=symbolData['starkExSyntheticAssetId'],
            collateral_id=currency['starkExAssetId'],
        )
        signature = order_to_sign.sign(self.stark_private_key)

        if side == ORDER_SIDE_BUY:
            human_cost = DECIMAL_CONTEXT_ROUND_UP.multiply(
                decimal.Decimal(size),
                decimal.Decimal(price)
            )
            fee = DECIMAL_CONTEXT_ROUND_UP.multiply(human_cost, decimal.Decimal(limitFee))
        else:
            human_cost = DECIMAL_CONTEXT_ROUND_DOWN.multiply(
                decimal.Decimal(size),
                decimal.Decimal(price)
            )
            fee = DECIMAL_CONTEXT_ROUND_DOWN.multiply(human_cost, decimal.Decimal(limitFee))

        limit_fee_rounded = DECIMAL_CONTEXT_ROUND_UP.quantize(
            decimal.Decimal(fee),
            decimal.Decimal(currency['stepSize']), )
        expirationEpoch = math.ceil(
            float(expirationEpochSeconds) / ONE_HOUR_IN_SECONDS,
        ) + ORDER_SIGNATURE_EXPIRATION_BUFFER_HOURS

        order = {
            'symbol': symbol,
            'side': side,
            'type': type,
            'timeInForce': timeInForce,
            'size': size,
            'price': price,
            'limitFee': str(limit_fee_rounded),
            'expiration': expirationEpoch * 3600 * 1000,
            'triggerPrice': triggerPrice,
            'trailingPercent': trailingPercent,
            'clientId': clientId,
            'signature': signature,
            'reduceOnly': reduceOnly,
        }

        path = URL_SUFFIX + "/v1/create-order"
        return self._post(
            endpoint=path,
            data=order
        )

    def create_withdrawal(self,
                          amount,
                          asset,
                          accountId=None,
                          clientId=None,
                          expiration=None,
                          expirationEpochSeconds=None,
                          ethAddress=None,
                          signature=None, ):
        """"
        POST  create-withdrawal-to-address.
       :returns: Request results as dictionary.
       """

        clientId = clientId or random_client_id()
        if not self.stark_private_key:
            raise Exception(
                'No signature provided and client was not ' +
                'initialized with stark_private_key'
            )

        if bool(expiration) == bool(expirationEpochSeconds):
            raise ValueError(
                'Exactly one of expiration and expiration_epoch_seconds must '
                'be specified',
            )
        expiration = expiration or epoch_seconds_to_iso(
            expirationEpochSeconds,
        )
        expirationEpochSeconds = (
                expirationEpochSeconds or iso_to_epoch_seconds(expiration)
        )

        ethAddress = ethAddress or self.account['ethereumAddress']
        if not ethAddress:
            raise Exception(
                'No ethAddress provided' +
                'please call user()'
            )

        accountId = accountId or self.account['positionId']
        if not accountId:
            raise Exception(
                'No accountId provided' +
                'please call account()'
            )

        if not self.config:
            raise Exception(
                'No config provided' +
                'please call configs()'
            )

        currency = {}

        for k, v in enumerate(self.config.get('currency')):
            if v.get('id') == asset:
                currency = v
        withdraw_to_sign = SignableWithdrawal(
            network_id=self.network_id,
            position_id=accountId,
            client_id=clientId,
            human_amount=amount,
            expiration_epoch_seconds=expirationEpochSeconds,
            eth_address=ethAddress,
            collateral_id=currency.get('starkExAssetId'),
        )
        signature = withdraw_to_sign.sign(self.stark_private_key)

        expirationEpoch = math.ceil(
            float(expirationEpochSeconds) / ONE_HOUR_IN_SECONDS,
        ) + ORDER_SIGNATURE_EXPIRATION_BUFFER_HOURS

        withdraw = {
            'amount': amount,
            'asset': asset,
            'expiration': expirationEpoch * 3600 * 1000,
            'ethAddress': ethAddress,
            'clientId': clientId,
            'signature': signature,
        }

        path = URL_SUFFIX + "/v1/create-withdrawal-to-address"
        return self._post(
            endpoint=path,
            data=withdraw
        )

    def fast_withdrawal(self,
                        amount,
                        asset,
                        accountId=None,
                        clientId=None,
                        expiration=None,
                        expirationEpochSeconds=None,
                        ethAddress=None,
                        erc20Address=None,
                        fee=None,
                        lpAccountId=None,
                        signature=None, ):
        """"
        POST  fast_withdrawal.
       :returns: Request results as dictionary.
       """

        clientId = clientId or random_client_id()
        if not self.stark_private_key:
            raise Exception(
                'No signature provided and client was not ' +
                'initialized with stark_private_key'
            )

        if bool(expiration) == bool(expirationEpochSeconds):
            raise ValueError(
                'Exactly one of expiration and expiration_epoch_seconds must '
                'be specified',
            )
        expiration = expiration or epoch_seconds_to_iso(
            expirationEpochSeconds,
        )
        expirationEpochSeconds = (
                expirationEpochSeconds or iso_to_epoch_seconds(expiration)
        )

        accountId = accountId or self.account['positionId']
        if not accountId:
            raise Exception(
                'No accountId provided' +
                'please call account()'
            )

        ethAddress = ethAddress or self.user['ethereumAddress']
        if not ethAddress:
            raise Exception(
                'No ethAddress provided' +
                'please call user()'
            )

        if not self.config:
            raise Exception(
                'No config provided' +
                'please call configs()'
            )

        currency = {}
        for k, v in enumerate(self.config['currency']):
            if v['id'] == asset:
                currency = v

        token = {}
        for k, v1 in enumerate(self.config['multiChain']['chains']):
            if v1['chainId'] == self.network_id:
                for _, v2 in enumerate(v1['tokens']):
                    if v2['token'] == asset:
                        token = v2

        fact = get_transfer_erc20_fact(
            recipient=ethAddress,
            token_decimals=token['decimals'],
            human_amount=amount,
            token_address=(
                token['tokenAddress']
            ),
            salt=nonce_from_client_id(clientId),
        )

        totalAmount = decimal.Decimal(amount) + decimal.Decimal(fee)
        transfer_to_sign = SignableConditionalTransfer(
            network_id=self.network_id,
            sender_position_id=accountId,
            receiver_position_id=self.config['global']['fastWithdrawAccountId'],
            receiver_public_key=self.config['global']['fastWithdrawL2Key'],
            fact_registry_address=self.config['global']['fastWithdrawFactRegisterAddress'],
            fact=fact,
            human_amount=str(totalAmount),
            client_id=clientId,
            expiration_epoch_seconds=expirationEpochSeconds,
            collateral_id=currency['starkExAssetId']
        )

        signature = transfer_to_sign.sign(self.stark_private_key)

        expirationEpoch = math.ceil(
            float(expirationEpochSeconds) / ONE_HOUR_IN_SECONDS,
        ) + ORDER_SIGNATURE_EXPIRATION_BUFFER_HOURS

        withdraw = {
            'amount': amount,
            'asset': asset,
            'expiration': expirationEpoch * 3600 * 1000,
            'ethAddress': ethAddress,
            'clientId': clientId,
            'signature': signature,
            'erc20Address': token['tokenAddress'],
            'fee': fee,
            'lpAccountId': self.config['global']['fastWithdrawAccountId'],
            'chainId': self.network_id
        }

        path = URL_SUFFIX + "/v1/fast-withdraw"
        return self._post(
            endpoint=path,
            data=withdraw
        )

    def cross_chain_withdraw(self,
                             amount,
                             asset,
                             chainId,
                             accountId=None,
                             clientId=None,
                             expiration=None,
                             expirationEpochSeconds=None,
                             erc20Address=None,
                             fee=None,
                             lpAccountId=None,
                             signature=None, ):
        """"
        POST  cross_chain_withdraw.
       :returns: Request results as dictionary.
       """
        clientId = clientId or random_client_id()
        if not self.stark_private_key:
            raise Exception(
                'No signature provided and client was not ' +
                'initialized with stark_private_key'
            )

        if bool(expiration) == bool(expirationEpochSeconds):
            raise ValueError(
                'Exactly one of expiration and expiration_epoch_seconds must '
                'be specified',
            )
        expiration = expiration or epoch_seconds_to_iso(
            expirationEpochSeconds,
        )
        expirationEpochSeconds = (
                expirationEpochSeconds or iso_to_epoch_seconds(expiration)
        )

        accountId = accountId or self.account['positionId']
        if not accountId:
            raise Exception(
                'No accountId provided' +
                'please call account()'
            )

        if not self.config:
            raise Exception(
                'No config provided' +
                'please call configs()'
            )

        currency = {}
        for k, v in enumerate(self.config['currency']):
            if v['id'] == asset:
                currency = v

        token = {}
        for k, v1 in enumerate(self.config['multiChain']['chains']):
            if v1['chainId'] == int(chainId):
                for _, v2 in enumerate(v1['tokens']):
                    if v2['token'] == asset:
                        token = v2

        totalAmount = decimal.Decimal(amount) + decimal.Decimal(fee)
        transfer_to_sign = SignableTransfer(
            network_id=chainId,
            sender_position_id=accountId,
            receiver_position_id=self.config['global']['crossChainAccountId'],
            receiver_public_key=self.config['global']['crossChainL2Key'],
            human_amount=str(totalAmount),
            client_id=clientId,
            expiration_epoch_seconds=expirationEpochSeconds,
            collateral_id=currency['starkExAssetId']
        )
        signature = transfer_to_sign.sign(self.stark_private_key)

        expirationEpoch = math.ceil(
            float(expirationEpochSeconds) / ONE_HOUR_IN_SECONDS,
        ) + ORDER_SIGNATURE_EXPIRATION_BUFFER_HOURS

        withdraw = {
            'amount': amount,
            'asset': asset,
            'expiration': expirationEpoch * 3600 * 1000,
            'clientId': clientId,
            'signature': signature,
            'erc20Address': token['tokenAddress'],
            'fee': fee,
            'lpAccountId': self.config['global']['crossChainAccountId'],
            'chainId': chainId
        }
        path = URL_SUFFIX + "/v1/cross-chain-withdraw"
        return self._post(
            endpoint=path,
            data=withdraw
        )
