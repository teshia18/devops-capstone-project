"""
Account API Service Test Suite

Test cases can be run with the following:
  nosetests -v --with-spec --spec-color
  coverage report -m
"""
import os
import logging
from unittest import TestCase
from tests.factories import AccountFactory
from service.common import status  # HTTP Status Codes
from service.models import db, Account, init_db
from service.routes import app
from service import app, talisman

DATABASE_URI = os.getenv(
    "DATABASE_URI", "postgresql://postgres:postgres@localhost:5432/postgres"
)

BASE_URL = "/accounts"
HTTPS_ENVIRON = {'wsgi.url_scheme': 'https'}


######################################################################
#  T E S T   C A S E S
######################################################################
class TestAccountService(TestCase):
    """Account Service Tests"""
    @classmethod
    def setUpClass(cls):
        """Run once before all tests"""
        talisman.force_https = False
        app.config["TESTING"] = True
        app.config["DEBUG"] = False
        app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URI
        app.logger.setLevel(logging.CRITICAL)
        init_db(app)
  
    @classmethod
    def tearDownClass(cls):
        """Runs once before test suite"""

    def setUp(self):
        """Runs before each test"""
        db.session.query(Account).delete()  # clean up the last tests
        db.session.commit()

        self.client = app.test_client()

    def tearDown(self):
        """Runs once after each test case"""
        db.session.remove()

    ######################################################################
    #  H E L P E R   M E T H O D S
    ######################################################################

    def _create_accounts(self, count):
        """Factory method to create accounts in bulk"""
        accounts = []
        for _ in range(count):
            account = AccountFactory()
            response = self.client.post(BASE_URL, json=account.serialize())
            self.assertEqual(
                response.status_code,
                status.HTTP_201_CREATED,
                "Could not create test Account",
            )
            new_account = response.get_json()
            account.id = new_account["id"]
            accounts.append(account)
        return accounts

    ######################################################################
    #  A C C O U N T   T E S T   C A S E S
    ######################################################################

    def test_index(self):
        """It should get 200_OK from the Home Page"""
        response = self.client.get("/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_health(self):
        """It should be healthy"""
        resp = self.client.get("/health")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data["status"], "OK")

    def test_create_account(self):
        """It should Create a new Account"""
        account = AccountFactory()
        response = self.client.post(
            BASE_URL, json=account.serialize(), content_type="application/json"
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Make sure location header is set
        location = response.headers.get("Location", None)
        self.assertIsNotNone(location)

        # Check the data is correct
        new_account = response.get_json()
        self.assertEqual(new_account["name"], account.name)
        self.assertEqual(new_account["email"], account.email)
        self.assertEqual(new_account["address"], account.address)
        self.assertEqual(new_account["phone_number"], account.phone_number)
        self.assertEqual(new_account["date_joined"], str(account.date_joined))

    def test_bad_request(self):
        """It should not Create an Account when sending the wrong data"""
        response = self.client.post(BASE_URL, json={"name": "not enough data"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_unsupported_media_type(self):
        """It should not Create an Account when sending the wrong media type"""
        account = AccountFactory()
        response = self.client.post(
            BASE_URL, json=account.serialize(), content_type="test/html"
        )
        self.assertEqual(response.status_code, status.HTTP_415_UNSUPPORTED_MEDIA_TYPE)

    # ADD YOUR TEST CASES HERE ...

    ######################################################################
    #  R E A D   A C C O U N T   T E S T   C A S E S
    ######################################################################

    def test_read_an_account(self):
        """It should Read a single Account"""
        # Create a mock account to test against using the helper method
        account = self._create_accounts(1)[0]

        # Make a GET request to read the created account
        response = self.client.get(f"{BASE_URL}/{account.id}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify that the returned JSON data matches what we originally created
        data = response.get_json()
        self.assertEqual(data["name"], account.name)

    def test_get_account_not_found(self):
        """It should not Read an Account that is not found"""
        # Query an invalid ID (0) that does not exist in the database
        response = self.client.get(f"{BASE_URL}/0")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    ######################################################################
    #  L I S T   A C C O U N T   T E S T   C A S E S
    ######################################################################

    def test_get_account_list(self):
        """It should Get a list of Accounts"""
        # Create 5 fake accounts in the test database
        self._create_accounts(5)

        # Send a GET request to the base URL endpoint
        response = self.client.get(BASE_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify the array contains exactly the 5 items we generated
        data = response.get_json()
        self.assertEqual(len(data), 5)

    ######################################################################
    #  U P D A T E   A C C O U N T   T E S T   C A S E S
    ######################################################################

    def test_update_account(self):
        """It should Update an existing Account"""
        # Create a mock account to test updating
        test_account = AccountFactory()
        response = self.client.post(BASE_URL, json=test_account.serialize())
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Get the account details from the response
        new_account = response.get_json()

        # Modify an attribute (changing the name to something known)
        new_account["name"] = "Updated Name Testing"

        # Send a PUT request to the specific account endpoint with the modified payload
        resp = self.client.put(f"{BASE_URL}/{new_account['id']}", json=new_account)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

        # Verify the returned account profile displays the updated name change
        updated_account = resp.get_json()
        self.assertEqual(updated_account["name"], "Updated Name Testing")

    def test_update_account_not_found(self):
        """It should not Update an Account that does not exist"""
        # Create a dummy payload to send
        dummy_account = AccountFactory().serialize()

        # Try to update an invalid ID (0)
        response = self.client.put(f"{BASE_URL}/0", json=dummy_account)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    ######################################################################
    #  D E L E T E   A C C O U N T   T E S T   C A S E S
    ######################################################################

    def test_delete_account(self):
        """It should Delete an Account"""
        # Create an account to test deletion against
        account = self._create_accounts(1)[0]

        # Send a DELETE request to the specific endpoint path
        response = self.client.get(f"{BASE_URL}/{account.id}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Request deletion of the target account profile record
        resp = self.client.delete(f"{BASE_URL}/{account.id}")
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)

        # Ensure that trying to read the deleted account now safely returns a 404
        check_resp = self.client.get(f"{BASE_URL}/{account.id}")
        self.assertEqual(check_resp.status_code, status.HTTP_404_NOT_FOUND)
    ######################################################################
    #  S E C U R I T Y   A N D   C O R S   T E S T   C A S E S
    ######################################################################
    def test_security_headers(self):
        """It should return secure security headers"""
        response = self.client.get("/", environ_overrides=HTTPS_ENVIRON)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        expected_headers = {
            'X-Frame-Options': 'SAMEORIGIN',
            'X-Content-Type-Options': 'nosniff',
            'Content-Security-Policy': "default-src 'self'; object-src 'none'",
            'Referrer-Policy': 'strict-origin-when-cross-origin'
        }
        for key, value in expected_headers.items():
            self.assertEqual(response.headers.get(key), value)
    def test_cors_security(self):
        """It should return standard CORS tracking access controls"""
        response = self.client.get("/", environ_overrides=HTTPS_ENVIRON)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.headers.get("Access-Control-Allow-Origin"), "*")
