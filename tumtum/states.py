import statesman


class ChallengeLifeCycle(statesman.StateMachine):
    class States(statesman.StateEnum):
        starting = 'Starting...'
        centering_face = 'Center face'
        positioning_nose = 'Move nose'
        verifying = 'Verifying'
        stopped = 'Stopped'

    @statesman.event(None, States.starting)
    async def start(self):
        pass

    @statesman.event(source=States.starting, target=States.centering_face)
    async def center_face(self):
        pass

    @statesman.event(source=States.centering_face, target=States.positioning_nose)
    async def position_nose(self):
        pass

    @statesman.event(source=States.positioning_nose, target=States.verifying)
    async def verify(self):
        pass

    @statesman.event(source=States.verifying, target=States.stopped)
    async def stop(self):
        pass


State = ChallengeLifeCycle.States
