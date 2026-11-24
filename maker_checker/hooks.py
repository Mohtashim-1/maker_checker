app_name = "maker_checker"
app_title = "Maker Checker"
app_publisher = "CodeCrest"
app_description = "Maker-Checker approval for Sales Invoice, Payment Entry, Journal Entry"
app_email = "admin@codecrestsolutions.com"
app_license = "mit"

required_apps = ["erpnext"]

after_install = ["maker_checker.setup.install.after_install"]
after_migrate = ["maker_checker.setup.install.after_migrate"]
