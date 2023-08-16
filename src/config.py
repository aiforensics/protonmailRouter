import yaml

class Config():
    def __init__(self, config_path="config.yaml" ) -> None:
        with open(config_path, "r") as stream:
            config = yaml.safe_load(stream)
        self.account = config['account']
        self.password = config['password']
        check_interval:int = config['checkIntervalMinutes']
        self.sleepTime = check_interval * 60
        self.distribution_list = {}
        for b in config['forwarding']:
            self.distribution_list[b['address'].lower()] = b['recipients']
