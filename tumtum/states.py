from typing import Optional

import gi
gi.require_version('Gtk', '3.0')

import statesman
from gi.repository import GObject, Gtk


class Pigeon(GObject.Object):
    @GObject.Signal('user-message', flags=GObject.SignalFlags.RUN_LAST, return_type=bool,
                    arg_types=(str, Gtk.MessageType),
                    accumulator=GObject.signal_accumulator_true_handled)
    def user_message(self, message: str, mtype: Gtk.MessageType.INFO):
        pass


class ChallengeLifeCycle(statesman.StateMachine):
    class States(statesman.StateEnum):
        starting = 'Starting...'
        centering_face = 'Center face'
        positioning_nose = 'Move nose'
        verifying = 'Verifying'
        success = 'Success'
        failed = 'Failed'
        stopped = 'Stopped'

    pigeon: Optional[Pigeon] = None

    class Config:
        arbitrary_types_allowed = True

    @statesman.event(None, States.starting)
    async def start(self, pigeon: Pigeon):
        self.pigeon = pigeon

    @statesman.event(source=States.starting, target=States.centering_face)
    async def center_face(self):
        self.show_guide('Put your face into the center of the box')

    @statesman.event(source=States.centering_face, target=States.positioning_nose)
    async def position_nose(self):
        self.show_guide('Put your nose to the yellow box')

    @statesman.event(source=States.positioning_nose, target=States.verifying)
    async def verify(self):
        self.show_guide('Verifying...')

    @statesman.event(source=States.verifying, target=States.success)
    async def finish_success(self):
        self.show_guide('Success')

    @statesman.event(source=States.verifying, target=States.failed)
    async def finish_failed(self, err_message=''):
        self.show_error(err_message or 'Verification failed')

    @statesman.event(source=States.verifying, target=States.stopped)
    async def stop(self):
        self.show_guide('Stopped')

    def show_guide(self, message: str):
        self.pigeon.emit('user-message', message, Gtk.MessageType.INFO)

    def show_error(self, message: str):
        self.pigeon.emit('user-message', message, Gtk.MessageType.ERROR)


State = ChallengeLifeCycle.States
