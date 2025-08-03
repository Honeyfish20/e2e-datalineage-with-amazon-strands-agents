"""
血缘数据模型

定义多源血缘数据、端到端路径和血缘图谱的数据结构。
"""

from dataclasses import dataclass, field
from typing import Dict, Optional, Any, List
from datetime import datetime
from enum import Enum


class CorrelationStatus(Enum):
    """关联状态枚举"""
    PENDING = "pending"
    CORRELATED = "correlated"
    FAILED = "failed"
    PARTIAL = "partial"


class GraphType(Enum):
    """图谱类型枚举"""
    EXECUTION_SPECIFIC = "execution_specific"
    AGGREGATED = "aggregated"
    HISTORICAL = "historical"


@dataclass
class MultiSourceLineageData:
    """多源血缘数据模型"""
    context_id: str
    glue_lineage: Optional[Dict[str, Any]] = None
    redshift_lineage: Optional[Dict[str, Any]] = None
    sagemaker_lineage: Optional[Dict[str, Any]] = None
    collection_timestamp: datetime = field(default_factory=datetime.now)
    correlation_status: CorrelationStatus = CorrelationStatus.PENDING
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def get_available_sources(self) -> List[str]:
        """获取可用的数据源列表"""
        sources = []
        if self.glue_lineage:
            sources.append('glue')
        if self.redshift_lineage:
            sources.append('redshift')
        if self.sagemaker_lineage:
            sources.append('sagemaker')
        return sources
    
    def is_complete(self) -> bool:
        """检查是否包含所有预期的数据源"""
        return len(self.get_available_sources()) >= 2  # 至少需要两个数据源
    
    def get_correlation_summary(self) -> Dict[str, Any]:
        """获取关联摘要"""
        return {
            'context_id': self.context_id,
            'available_sources': self.get_available_sources(),
            'sources_count': len(self.get_available_sources()),
            'correlation_status': self.correlation_status.value,
            'is_complete': self.is_complete(),
            'collection_timestamp': self.collection_timestamp.isoformat()
        }


@dataclass
class EndToEndLineagePath:
    """端到端血缘路径模型"""
    path_id: str
    context_id: str
    source_entities: List[Dict[str, Any]]
    target_entities: List[Dict[str, Any]]
    intermediate_steps: List[Dict[str, Any]]
    services_involved: List[str]  # ['glue', 'redshift', 'sagemaker']
    path_confidence: float
    creation_timestamp: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def get_path_length(self) -> int:
        """获取路径长度"""
        return len(self.intermediate_steps) + 1
    
    def get_path_summary(self) -> str:
        """获取路径摘要"""
        source_names = [entity.get('name', 'unknown') for entity in self.source_entities]
        target_names = [entity.get('name', 'unknown') for entity in self.target_entities]
        
        return f"Path from {', '.join(source_names)} to {', '.join(target_names)} via {' -> '.join(self.services_involved)}"
    
    def calculate_impact_scope(self, change_point: str) -> List[str]:
        """计算变更影响范围"""
        impact_entities = []
        
        # 查找变更点在路径中的位置
        change_found = False
        for step in self.intermediate_steps:
            if change_found:
                impact_entities.append(step.get('entity_id', ''))
            elif step.get('entity_id') == change_point:
                change_found = True
        
        # 如果变更点在中间步骤中找到，添加目标实体
        if change_found:
            impact_entities.extend([entity.get('id', '') for entity in self.target_entities])
        
        return impact_entities
    
    def get_services_sequence(self) -> List[str]:
        """获取服务调用序列"""
        sequence = []
        for step in self.intermediate_steps:
            service = step.get('service', 'unknown')
            if service not in sequence:
                sequence.append(service)
        return sequence


@dataclass
class LineageGraph:
    """完整血缘图谱模型"""
    graph_id: str
    context_id: str
    created_timestamp: datetime
    
    # 图谱组件
    nodes: List[Dict[str, Any]]
    edges: List[Dict[str, Any]]
    paths: List[EndToEndLineagePath]
    
    # 图谱统计
    total_nodes: int
    total_edges: int
    total_paths: int
    
    # 数据源统计
    data_sources_count: int
    data_targets_count: int
    transformations_count: int
    
    # 服务统计
    glue_components: int
    redshift_components: int
    sagemaker_components: int
    
    # 图谱类型和元数据
    graph_type: GraphType = GraphType.EXECUTION_SPECIFIC
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def find_paths(self, source: str, target: str) -> List[List[str]]:
        """查找源到目标的所有路径"""
        paths = []
        
        # 构建邻接表
        adjacency = {}
        for edge in self.edges:
            from_node = edge.get('from_node_id', '')
            to_node = edge.get('to_node_id', '')
            
            if from_node not in adjacency:
                adjacency[from_node] = []
            adjacency[from_node].append(to_node)
        
        # 深度优先搜索查找路径
        def dfs(current: str, target: str, path: List[str], visited: set):
            if current == target:
                paths.append(path + [current])
                return
            
            if current in visited:
                return
            
            visited.add(current)
            for neighbor in adjacency.get(current, []):
                dfs(neighbor, target, path + [current], visited.copy())
        
        dfs(source, target, [], set())
        return paths
    
    def get_upstream_dependencies(self, entity: str) -> List[str]:
        """获取上游依赖"""
        upstream = []
        for edge in self.edges:
            if edge.get('to_node_id') == entity:
                upstream.append(edge.get('from_node_id', ''))
        return upstream
    
    def get_downstream_impacts(self, entity: str) -> List[str]:
        """获取下游影响"""
        downstream = []
        for edge in self.edges:
            if edge.get('from_node_id') == entity:
                downstream.append(edge.get('to_node_id', ''))
        return downstream
    
    def get_graph_statistics(self) -> Dict[str, Any]:
        """获取图谱统计信息"""
        return {
            'graph_id': self.graph_id,
            'context_id': self.context_id,
            'graph_type': self.graph_type.value,
            'created_timestamp': self.created_timestamp.isoformat(),
            'components': {
                'total_nodes': self.total_nodes,
                'total_edges': self.total_edges,
                'total_paths': self.total_paths
            },
            'node_types': {
                'data_sources': self.data_sources_count,
                'data_targets': self.data_targets_count,
                'transformations': self.transformations_count
            },
            'services': {
                'glue_components': self.glue_components,
                'redshift_components': self.redshift_components,
                'sagemaker_components': self.sagemaker_components
            }
        }
    
    def validate_graph_integrity(self) -> bool:
        """验证图谱完整性"""
        # 检查节点和边的一致性
        node_ids = {node.get('id', '') for node in self.nodes}
        
        for edge in self.edges:
            from_node = edge.get('from_node_id', '')
            to_node = edge.get('to_node_id', '')
            
            if from_node not in node_ids or to_node not in node_ids:
                return False
        
        # 检查统计数据的一致性
        if (self.total_nodes != len(self.nodes) or 
            self.total_edges != len(self.edges) or
            self.total_paths != len(self.paths)):
            return False
        
        return True