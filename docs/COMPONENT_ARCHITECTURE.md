# Component-Based Architecture with Discovery-Processing-Housekeeping Pattern

This document outlines the new component-based architecture we're implementing in the r630-iscsi-switchbot project. This architecture provides a consistent approach to all operations using a discovery-processing-housekeeping pattern.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     Orchestration Layer                     │
│                                                             │
│ ┌─────────────┐  ┌─────────────┐  ┌─────────────┐           │
│ │ Full        │  │ OpenShift   │  │ iSCSI Boot  │  ...      │
│ │ Deployment  │  │ Only        │  │ Only        │           │
│ └─────────────┘  └─────────────┘  └─────────────┘           │
└─────────────────────────────────────────────────────────────┘
                           │
┌─────────────────────────────────────────────────────────────┐
│                     Component Layer                         │
│                                                             │
│ ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────┐  │
│ │ OpenShift   │  │ iSCSI       │  │ Dell R630   │  │ S3  │  │
│ │ Component   │  │ Component   │  │ Component   │  │ ... │  │
│ └─────────────┘  └─────────────┘  └─────────────┘  └─────┘  │
└─────────────────────────────────────────────────────────────┘
                           │
┌─────────────────────────────────────────────────────────────┐
│                     Core Framework Layer                    │
│ ┌─────────────┐  ┌─────────────┐  ┌─────────────┐           │
│ │ Discovery   │  │ Processing  │  │ Housekeeping│  ...      │
│ │ Framework   │  │ Framework   │  │ Framework   │           │
│ └─────────────┘  └─────────────┘  └─────────────┘           │
└─────────────────────────────────────────────────────────────┘
```

## Discovery-Processing-Housekeeping Pattern

Each component in our architecture implements a consistent three-phase lifecycle:

### 1. Discovery Phase

**Purpose**: Examine the current environment without making changes.

**Activities**:
- Verify connectivity to required services
- Check for existing resources
- Identify available and required components
- Detect current configurations
- Validate prerequisites
- Gather relevant system information

**Outputs**:
- Discovery results (dictionary/JSON)
- Logs of detected resources
- Validation checks

### 2. Processing Phase

**Purpose**: Perform the core work of the component based on discovery results.

**Activities**:
- Create or update resources
- Configure systems
- Generate files or artifacts
- Deploy configurations
- Make changes to the environment

**Outputs**:
- Processing results (dictionary/JSON)
- Created artifacts
- Status of operations
- S3 storage references

### 3. Housekeeping Phase

**Purpose**: Verify, clean up, and finalize the component's work.

**Activities**:
- Validate changes were successful
- Clean up temporary resources
- Update configuration repositories
- Perform final verifications
- Archive artifacts with metadata
- Prepare for next execution

**Outputs**:
- Housekeeping results (dictionary/JSON)
- Verification status
- Cleanup summary
- Generated metadata

## Component Structure

Each component follows a standard structure:

```python
class ComponentBase:
    def __init__(self, config, logger=None):
        self.config = config
        self.logger = logger or logging.getLogger(self.__class__.__name__)
        self.discovery_results = {}
        self.processing_results = {}
        self.housekeeping_results = {}
        self.artifacts = []
        
    def discover(self):
        """Discovery phase implementation"""
        pass
        
    def process(self):
        """Processing phase implementation"""
        pass
        
    def housekeep(self):
        """Housekeeping phase implementation"""
        pass
        
    def execute(self, phases=["discover", "process", "housekeep"]):
        """Execute all or specific phases"""
        pass
```

## Specialized Components

### OpenShiftComponent

Handles OpenShift ISO creation and configuration:

- **Discovery**: Find existing ISOs, check version requirements
- **Processing**: Generate new ISOs if needed
- **Housekeeping**: Verify ISO integrity, publish to public S3

### ISCSIComponent

Manages iSCSI target creation and configuration:

- **Discovery**: Check TrueNAS connectivity, list existing targets
- **Processing**: Create or update iSCSI targets
- **Housekeeping**: Verify target accessibility, update configurations

### R630Component

Configures Dell R630 hardware:

- **Discovery**: Check iDRAC connectivity, get hardware info
- **Processing**: Configure network, boot order, virtual media
- **Housekeeping**: Verify configuration, reboot if needed

### S3Component

Manages S3 storage and artifacts:

- **Discovery**: Check S3 endpoints, list buckets and objects
- **Processing**: Upload artifacts, manage dual buckets
- **Housekeeping**: Verify uploads, maintain metadata index

## Orchestration Layer

The orchestration layer coordinates multiple components to implement specific workflows. Examples include:

- **Full Deployment**: Coordinates all components for complete deployment
- **OpenShift Only**: Just handles OpenShift ISO creation
- **iSCSI Boot Only**: Configures iSCSI boot without rebuilding OpenShift

## S3 Integration

All components integrate with S3 storage for artifact management:

- **Private bucket** stores all artifacts with versioning
- **Public bucket** provides anonymous access to selected resources
- Artifacts include metadata for tracking and lifecycle management
- A metadata index provides discoverability

## CI/CD Integration

This architecture is designed for pipeline integration:

- Components use standardized logging to stdout
- Operations can be parameterized for automation
- All artifacts are stored in S3 for persistence
- Results are structured for programmatic use

## Implementation Guidelines

When implementing components:

1. **Start with Discovery**: Always begin with thorough discovery
2. **State-Based Processing**: Base processing decisions on discovery results
3. **Verify Everything**: Use housekeeping to validate all changes
4. **Store Artifacts**: Save all important outputs to S3
5. **Detailed Logging**: Log all operations at appropriate levels
6. **Handle Failures**: Implement proper error handling and rollback

## Migration Strategy

The transition to this architecture will be gradual:

1. Implement the core framework
2. Create one component at a time
3. Maintain backward compatibility
4. Gradually replace existing scripts
5. Document the new approach thoroughly

See the [Project Roadmap](../README.md#project-roadmap-discovery-processing-housekeeping-implementation) for detailed migration plans.
