# Import all models so Base.metadata.create_all() creates every table (e.g. suppliers, materials).
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
