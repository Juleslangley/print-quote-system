# Import all models so Base.metadata.create_all() creates every table (e.g. suppliers, materials).
from .user import User
from .customer import Customer
from .customer_contact import CustomerContact
from .customer_contact_method import CustomerContactMethod
from .material import Material
from .material_size import MaterialSize
from .supplier import Supplier
from .rate import Rate
from .template import ProductTemplate
from .quote import Quote, QuoteItem
from .machine import Machine
from .machine_rate import MachineRate
from .operation import Operation
from .template_links import TemplateOperation, TemplateAllowedMaterial
from .margin_profile import MarginProfile
from .pricing_rules import TemplatePricingRule, CustomerPricingRule
from .purchase_order import PurchaseOrder
from .purchase_order_line import PurchaseOrderLine
from .po_sequence import POSequence
from .supplier_invoice import SupplierInvoice
