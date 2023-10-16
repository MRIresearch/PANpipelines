from panpipelines import Factory
from panpipelines.pipelines.aslprep_panpipeline import aslprep_panpipeline

def test_PANFactory_getpipeline() -> None:
    panFactory = Factory.getPANFactory()
    assert panFactory.get_processflow("aslprep_panpipeline") == aslprep_panpipeline