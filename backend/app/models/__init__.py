# Import all models so Base.metadata is complete (for Alembic autogenerate and ORM).
from .user import User
from .customer import Customer
from .material import Material
from .supplier import Supplier
from .rate import Rate
from .template import ProductTemplate
from .quote import Quote, QuoteItem
from .machine import Machine
from .operation import Operation
from .template_links import TemplateOperation, TemplateAllowedMaterial
from .margin_profile import MarginProfile
from .pricing_rules import TemplatePricingRule, CustomerPricingRule
from .purchase_order import PurchaseOrder
from .purchase_order_line import PurchaseOrderLine
from .job_no_sequence import JobNoSequence
from .job import Job
from .job_version import JobVersion
from .file import File
from .file_link import FileLink
from .events_outbox import EventsOutbox
from .packing_batch import PackingBatch
from .packing_store_job import PackingStoreJob
from .packing_store_line_item import PackingStoreLineItem

# Document system (v1 templates + renders)
from .document_template import DocumentTemplate
from .document_render import DocumentRender
