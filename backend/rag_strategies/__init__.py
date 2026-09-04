from .adaptive import AdaptiveRAG
from .advanced import AdvancedRAG
from .agent import AgentRAG
from .corrective import CorrectiveRAG
from .graph import GraphRAG
from .hybrid import HybridRAG
from .multimodal import MultimodalRAG
from .naive import NaiveRAG

STRATEGIES = {strategy.name: strategy for strategy in (NaiveRAG(), AdvancedRAG(), CorrectiveRAG(), AgentRAG(), AdaptiveRAG(), GraphRAG(), HybridRAG(), MultimodalRAG())}
