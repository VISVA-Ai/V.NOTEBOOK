# Handles knowledge graph construction
import networkx as nx
import matplotlib.pyplot as plt
from io import BytesIO

class KnowledgeGraph:
    def __init__(self):
        self.graph = nx.Graph()
        
    def build_graph(self, documents):
        self.graph.clear()
        for i, doc in enumerate(documents):
            node_id = f"Chunk {i+1}"
            label = doc['text'][:20] + "..."
            self.graph.add_node(node_id, label=label, text=doc['text'])
            if i > 0:
                prev_node = f"Chunk {i}"
                self.graph.add_edge(prev_node, node_id)
                
    def get_graph_html(self):
        pass
