from AWSIoTPythonSDK.MQTTLib import AWSIoTMQTTClient

myMQTTClient = AWSIoTMQTTClient("jp_elv")
myMQTTClient.configureEndpoint("amo0fvup7bx7k-ats.iot.eu-west-1.amazonaws.com", 8883)
myMQTTClient.configureCredentials("AmazonRootCA1.pem", "jp_elv_private.key", "jp_elv.crt")
myMQTTClient.connect()
myMQTTClient.publish("USER1", "myPayload", 0)
myMQTTClient.disconnect()
