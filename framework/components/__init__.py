"""
Components Package for r630-iscsi-switchbot Component Architecture

This package contains specialized components that implement the
discovery-processing-housekeeping pattern for specific system aspects.
"""

# Import component classes
from .s3_component import S3Component
from .openshift_component import OpenShiftComponent
from .iscsi_component import ISCSIComponent
from .r630_component import R630Component

# Update __all__ list with implemented components
__all__ = ['S3Component', 'OpenShiftComponent', 'ISCSIComponent', 'R630Component']
