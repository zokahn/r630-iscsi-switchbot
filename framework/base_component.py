#!/usr/bin/env python3
"""
Base Component Class for Discovery-Processing-Housekeeping Pattern

This module provides the BaseComponent class that all specialized components
should inherit from to implement the discovery-processing-housekeeping pattern.
"""

import logging
import os
import json
import datetime
import traceback
import uuid
from typing import Dict, List, Any, Optional, Union
from pathlib import Path

class BaseComponent:
    """
    Base class for all components in the system.
    
    Implements the discovery-processing-housekeeping pattern and provides
    common functionality for component lifecycle management.
    """
    
    def __init__(self, config: Dict[str, Any], logger: Optional[logging.Logger] = None):
        """
        Initialize a new component instance.
        
        Args:
            config: Configuration dictionary for the component
            logger: Optional logger instance (if not provided, a new one will be created)
        """
        self.config = config
        self.component_id = config.get('component_id', str(uuid.uuid4()))
        self.component_name = self.__class__.__name__
        
        # Setup logging
        self.logger = logger or self._setup_logger()
        
        # Initialize phase results
        self.discovery_results: Dict[str, Any] = {}
        self.processing_results: Dict[str, Any] = {}
        self.housekeeping_results: Dict[str, Any] = {}
        
        # Initialize artifacts list
        self.artifacts: List[Dict[str, Any]] = []
        
        # Execution state tracking
        self.phases_executed = {
            'discover': False,
            'process': False,
            'housekeep': False
        }
        
        # Execution timestamps
        self.timestamps = {
            'start': None,
            'discover_start': None,
            'discover_end': None,
            'process_start': None, 
            'process_end': None,
            'housekeep_start': None,
            'housekeep_end': None,
            'end': None
        }
        
        # Execution status
        self.status = {
            'success': False,
            'error': None,
            'message': None
        }
        
        self.logger.info(f"Initialized {self.component_name} (ID: {self.component_id})")
    
    def _setup_logger(self) -> logging.Logger:
        """
        Set up a logger for this component.
        
        Returns:
            A configured logger instance
        """
        logger = logging.getLogger(self.component_name)
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
        return logger
    
    def discover(self) -> Dict[str, Any]:
        """
        Discovery phase: Examine the current environment without making changes.
        
        This method should be overridden by derived classes to implement
        specific discovery logic.
        
        Returns:
            Dictionary of discovery results
        """
        self.timestamps['discover_start'] = datetime.datetime.now().isoformat()
        self.logger.info(f"Starting discovery phase for {self.component_name}")
        
        try:
            # Implementation should be provided by derived classes
            self.logger.warning(f"Default discovery implementation called for {self.component_name}")
            
            # Mark as executed
            self.phases_executed['discover'] = True
            
            # Update timestamp
            self.timestamps['discover_end'] = datetime.datetime.now().isoformat()
            self.logger.info(f"Discovery phase completed for {self.component_name}")
            
            return self.discovery_results
            
        except Exception as e:
            self.logger.error(f"Error during discovery phase: {str(e)}")
            self.logger.debug(traceback.format_exc())
            self.status['success'] = False
            self.status['error'] = str(e)
            self.status['message'] = f"Discovery phase failed: {str(e)}"
            
            # Update timestamp even on failure
            self.timestamps['discover_end'] = datetime.datetime.now().isoformat()
            
            raise
    
    def process(self) -> Dict[str, Any]:
        """
        Processing phase: Perform the core work of the component.
        
        This method should be overridden by derived classes to implement
        specific processing logic.
        
        Returns:
            Dictionary of processing results
        """
        self.timestamps['process_start'] = datetime.datetime.now().isoformat()
        self.logger.info(f"Starting processing phase for {self.component_name}")
        
        # Check if discovery has been run
        if not self.phases_executed['discover']:
            self.logger.warning("Processing without prior discovery may lead to unexpected results")
        
        try:
            # Implementation should be provided by derived classes
            self.logger.warning(f"Default processing implementation called for {self.component_name}")
            
            # Mark as executed
            self.phases_executed['process'] = True
            
            # Update timestamp
            self.timestamps['process_end'] = datetime.datetime.now().isoformat()
            self.logger.info(f"Processing phase completed for {self.component_name}")
            
            return self.processing_results
            
        except Exception as e:
            self.logger.error(f"Error during processing phase: {str(e)}")
            self.logger.debug(traceback.format_exc())
            self.status['success'] = False
            self.status['error'] = str(e)
            self.status['message'] = f"Processing phase failed: {str(e)}"
            
            # Update timestamp even on failure
            self.timestamps['process_end'] = datetime.datetime.now().isoformat()
            
            raise
    
    def housekeep(self) -> Dict[str, Any]:
        """
        Housekeeping phase: Verify, clean up, and finalize the component's work.
        
        This method should be overridden by derived classes to implement
        specific housekeeping logic.
        
        Returns:
            Dictionary of housekeeping results
        """
        self.timestamps['housekeep_start'] = datetime.datetime.now().isoformat()
        self.logger.info(f"Starting housekeeping phase for {self.component_name}")
        
        # Check if processing has been run
        if not self.phases_executed['process']:
            self.logger.warning("Housekeeping without prior processing may lead to unexpected results")
        
        try:
            # Implementation should be provided by derived classes
            self.logger.warning(f"Default housekeeping implementation called for {self.component_name}")
            
            # Mark as executed
            self.phases_executed['housekeep'] = True
            
            # Update timestamp
            self.timestamps['housekeep_end'] = datetime.datetime.now().isoformat()
            self.logger.info(f"Housekeeping phase completed for {self.component_name}")
            
            # Store artifacts
            if self.artifacts:
                self._store_artifacts()
            
            return self.housekeeping_results
            
        except Exception as e:
            self.logger.error(f"Error during housekeeping phase: {str(e)}")
            self.logger.debug(traceback.format_exc())
            self.status['success'] = False
            self.status['error'] = str(e)
            self.status['message'] = f"Housekeeping phase failed: {str(e)}"
            
            # Update timestamp even on failure
            self.timestamps['housekeep_end'] = datetime.datetime.now().isoformat()
            
            raise
    
    def execute(self, phases: List[str] = ["discover", "process", "housekeep"]) -> Dict[str, Any]:
        """
        Execute the component lifecycle phases.
        
        Args:
            phases: List of phases to execute (default: all phases)
            
        Returns:
            Dictionary with the results of all executed phases
        """
        self.timestamps['start'] = datetime.datetime.now().isoformat()
        self.logger.info(f"Executing {self.component_name} with phases: {', '.join(phases)}")
        
        results = {}
        
        try:
            # Execute requested phases
            if "discover" in phases:
                results["discovery"] = self.discover()
                
            if "process" in phases:
                results["processing"] = self.process()
                
            if "housekeep" in phases:
                results["housekeeping"] = self.housekeep()
            
            # Mark as successful if we got here
            self.status['success'] = True
            self.status['message'] = f"Execution completed successfully"
            
        except Exception as e:
            # Status will be updated by the specific phase that failed
            results["error"] = str(e)
            results["traceback"] = traceback.format_exc()
            
            # Attempt to store what we have so far even on failure
            if self.artifacts:
                try:
                    self._store_artifacts()
                except Exception as artifact_e:
                    self.logger.error(f"Error storing artifacts after failure: {str(artifact_e)}")
            
        finally:
            # Always update end timestamp
            self.timestamps['end'] = datetime.datetime.now().isoformat()
            
            # Add execution metadata to results
            results["metadata"] = {
                "component_id": self.component_id,
                "component_name": self.component_name,
                "timestamps": self.timestamps,
                "phases_executed": self.phases_executed,
                "status": self.status
            }
            
            self.logger.info(f"Execution of {self.component_name} completed with status: {self.status['success']}")
            
            return results
    
    def add_artifact(self, artifact_type: str, content: Any, metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Add an artifact to be stored during housekeeping.
        
        Args:
            artifact_type: Type of artifact (e.g., 'iso', 'config', 'log')
            content: The artifact content or path
            metadata: Additional metadata for the artifact
            
        Returns:
            Artifact ID
        """
        artifact_id = str(uuid.uuid4())
        
        # Combine provided metadata with standard metadata
        artifact_metadata = {
            "artifact_id": artifact_id,
            "artifact_type": artifact_type,
            "component_id": self.component_id,
            "component_name": self.component_name,
            "timestamp": datetime.datetime.now().isoformat(),
            **(metadata or {})
        }
        
        # Add to artifacts list
        self.artifacts.append({
            "id": artifact_id,
            "type": artifact_type,
            "content": content,
            "metadata": artifact_metadata
        })
        
        self.logger.debug(f"Added artifact: {artifact_id} ({artifact_type})")
        
        return artifact_id
    
    def _store_artifacts(self) -> None:
        """
        Store all registered artifacts.
        
        This is a placeholder that should be implemented by a concrete S3Component
        or similar. The base implementation logs the artifacts for debugging.
        """
        if not self.artifacts:
            self.logger.debug("No artifacts to store")
            return
            
        self.logger.info(f"Would store {len(self.artifacts)} artifacts")
        for artifact in self.artifacts:
            self.logger.debug(f"Would store artifact: {artifact['id']} ({artifact['type']})")
            
            # In a real implementation, this would use S3 or other storage
            # For example:
            # s3_component.store_artifact(artifact['type'], artifact['content'], artifact['metadata'])
        
    def get_execution_summary(self) -> Dict[str, Any]:
        """
        Get a summary of this component's execution.
        
        Returns:
            Dictionary with execution summary
        """
        return {
            "component_id": self.component_id,
            "component_name": self.component_name,
            "status": self.status,
            "timestamps": self.timestamps,
            "phases_executed": self.phases_executed,
            "artifacts_count": len(self.artifacts),
            "discovery_results_count": len(self.discovery_results),
            "processing_results_count": len(self.processing_results),
            "housekeeping_results_count": len(self.housekeeping_results)
        }
    
    def to_json(self) -> str:
        """
        Convert component results to a JSON string.
        
        Returns:
            JSON string representation of the component results
        """
        results = {
            "component_id": self.component_id,
            "component_name": self.component_name,
            "timestamps": self.timestamps,
            "phases_executed": self.phases_executed,
            "status": self.status,
            "discovery_results": self.discovery_results,
            "processing_results": self.processing_results,
            "housekeeping_results": self.housekeeping_results,
            "artifacts": [
                {
                    "id": a["id"],
                    "type": a["type"],
                    "metadata": a["metadata"]
                } 
                for a in self.artifacts
            ]
        }
        
        return json.dumps(results, indent=2)
