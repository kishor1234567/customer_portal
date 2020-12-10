from __future__ import print_function

import firebase_admin
from firebase_admin import credentials

import datetime
from firebase_admin import messaging

cred = credentials.Certificate(
    "/home/frappe/frappe-bench/env/cq5o5-c49728f7e3.json")


class FcmUtils():
    def __init__(self):
        firebase_admin.initialize_app(cred)

    def test_message(self):
        # [START send_to_token]
        # This registration token comes from the client FCM SDKs.
        registration_token = 'd4KUpt5mSJ6ngrNytzwYsp:APA91bGru82_I4TshgwfWhTlq-B-hmqD31nWLr_-3VA_NeUrG3JneaQtuK7et7R_lQS4BGly8nkH7CWC3RIeU3fob46VnO_kq1giPV_EZIi-MOPXDkHpULtYEp2A8fcm12MOvJyNTU3s'

        # See documentation on defining a message payload.
        message = messaging.Message(
            notification=messaging.Notification(
                title='$GOOG up 1.43% on the day',
                body='$GOOG gained 11.80 points to close at 835.67, up 1.43% on the day.',
            ),
            android=messaging.AndroidConfig(
                ttl=datetime.timedelta(seconds=3600),
                priority='normal',
                notification=messaging.AndroidNotification(
                    icon='stock_ticker_update',
                    color='#f45342'
                ),
            ),
            apns=messaging.APNSConfig(
                payload=messaging.APNSPayload(
                    aps=messaging.Aps(badge=42),
                ),
            ),
            token=registration_token,
        )

        # Send a message to the device corresponding to the provided
        # registration token.
        response = messaging.send(message)
        # Response is a message ID string.
        print('Successfully sent message:', response)
        # [END send_to_token]

    def send_single_notification(self, message, data, token):
        self.message = message
        self.data = data
        self.token = token
        message = self.construct_single_message()
        return messaging.send(message)

    def construct_single_message(self):
        self.data['click_action'] = 'FLUTTER_NOTIFICATION_CLICK'
        message = messaging.Message(
            notification=messaging.Notification(
                title=self.message['title'],
                body=self.message['body'],
            ),
            android=messaging.AndroidConfig(
                ttl=datetime.timedelta(seconds=3600),
                priority='normal',
            ),
            apns=messaging.APNSConfig(
                payload=messaging.APNSPayload(
                    aps=messaging.Aps(badge=42),
                ),
            ),
            data=self.data,
            token=self.token,
        )
        return message

    def construct_multicast_message(self):
        self.data['click_action'] = 'FLUTTER_NOTIFICATION_CLICK'
        message = messaging.MulticastMessage(
            notification=messaging.Notification(
                title=self.message['title'],
                body=self.message['body'],
            ),
            android=messaging.AndroidConfig(
                ttl=datetime.timedelta(seconds=3600),
                priority='normal',
            ),
            apns=messaging.APNSConfig(
                payload=messaging.APNSPayload(
                    aps=messaging.Aps(badge=42),
                ),
            ),
            data=self.data,
            tokens=self.tokens,
        )
        return message

    def send_multicast_notification(self, message, data, tokens):
        self.message = message
        self.data = data
        self.tokens = tokens
        message = self.construct_multicast_message()
        res = messaging.send_multicast(message)
        # remove_erroneous_devices(res)
        return res

    def remove_erroneous_devices(responses):
        print(res.responses)
        for e in res.responses:
            if e.exception == "Requested entity was not found.":
                pass
