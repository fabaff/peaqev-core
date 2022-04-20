import time
from datetime import datetime
from Models import CHARGERSTATES

class ChargeControllerBase:
    def __init__(
        self,
        charger_state_translation:dict[CHARGERSTATES,list[str]],
        non_hours:list[int] = [],
        timeout:int = 180
    ):
        self._done_timeout = timeout
        self._latest_charger_start = time.time()
        self._charger_state_translation = self._check_charger_states(charger_state_translation)
        self._non_hours = non_hours
    
    @property
    def done_timeout(self):
        return self._done_timeout

    def below_start_threshold(
            self,
            predicted_energy: float,
            current_peak: float,
            threshold_start: float
    ) -> bool:
        return (predicted_energy * 1000) < ((current_peak * 1000) * (threshold_start / 100))

    def above_stop_threshold(
            self,
            predicted_energy: float,
            current_peak: float,
            threshold_stop: float
    ) -> bool:
        return (predicted_energy * 1000) > ((current_peak * 1000) * (threshold_stop / 100))

    @property
    def latest_charger_start(self):
        return self._latest_charger_start

    @latest_charger_start.setter
    def latest_charger_start(self, val=None):
        self._latest_charger_start = time.time()

    
    @property
    def _is_timeout(self) -> bool:
        return time.time() - self.latest_charger_start > self._done_timeout

    def _check_charger_states(self, input:dict[CHARGERSTATES,list[str]]) -> dict[CHARGERSTATES,list[str]]:
        for i in input.keys:
            if len(input[i]) == 0:
                raise Exception
        return input

    def _get_status(
        self,
        charger_state:str,
        charger_enabled:bool,
        charger_done:bool,
        car_power_sensor:float,
        total_energy_this_hour:float,
        current_hour:int|None
        ):
        _update_timer = False
        self._charger_state = charger_state.lower()
        self._current_hour = current_hour if current_hour is not None else datetime.now().hour
        ret = CHARGERSTATES.Error

        if self._charger_state in self._charger_state_translation[CHARGERSTATES.Idle]:
            _update_timer = True
            ret = CHARGERSTATES.Idle

        elif self._charger_state in self._charger_state_translation[CHARGERSTATES.Connected] and charger_enabled is False:
            _update_timer = True
            ret = CHARGERSTATES.Connected

        elif self._charger_state not in self._charger_state_translation[CHARGERSTATES.Idle] and charger_done is True:
            ret = CHARGERSTATES.Done

        elif self._current_hour in self._non_hours:
            _update_timer = True
            ret = CHARGERSTATES.Stop

        elif self._charger_state in self._charger_state_translation[CHARGERSTATES.Connected]:
            if car_power_sensor < 1 and self._is_timeout:
                ret = CHARGERSTATES.Done
            else:
                if self.below_start_threshold and total_energy_this_hour > 0:
                    ret = CHARGERSTATES.Start
                else:
                    _update_timer = True
                    ret = CHARGERSTATES.Stop

        elif self._charger_state in self._charger_state_translation[CHARGERSTATES.Charging]:
            _update_timer = True
            if self.above_stop_threshold and total_energy_this_hour > 0:
                ret = CHARGERSTATES.Stop
            else:
                ret = CHARGERSTATES.Start

        if _update_timer is True:
            self.latest_charger_start = 1
        return ret