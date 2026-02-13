# Re-export from deps to avoid circular import (deps has get_current_user + role guards)
from app.api.deps import (
    get_current_user,
    require_roles,
    require_admin,
    require_sales,
    require_prod_or_better,
    require_packer,
)
