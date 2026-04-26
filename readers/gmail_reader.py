import os.path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# If modifying these scopes, delete the file token.json.
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]


def get_profile_history_id(service):
  profile = service.users().getProfile(userId='me').execute()
  return profile['historyId']
  

def gmail_check():
  """Shows basic usage of the Gmail API.
  Lists the user's Gmail labels.
  """
  creds = None
  if os.path.exists("token.json"):
    creds = Credentials.from_authorized_user_file("token.json", SCOPES)
  # If there are no (valid) credentials available, let the user log in.
  if not creds or not creds.valid:
    if creds and creds.expired and creds.refresh_token:
      creds.refresh(Request())
    else:
      flow = InstalledAppFlow.from_client_secrets_file(
          "credentials.json", SCOPES
      )
      creds = flow.run_local_server(port=0)
    # Save the credentials for the next run
    with open("token.json", "w") as token:
      token.write(creds.to_json())

  try:
    # Call the Gmail API
    service = build("gmail", "v1", credentials=creds)
    
    if not history_id: 
      history_id = get_profile_history_id(service)
    
    result_history = service.users().history().list(userId="me", startHistoryId=history_id).execute()

    message_list = list

    if 'history' in result_history:
      for register in result_history['history']:
          if 'messagesAdded' in register:
              for message in register['messagesAdded']:
                  message_list.append(message["message"]["id"])

    history_id = result_history["historyId"]

    emails_details = tuple
    for message in message_list:
      emails_details.append(service.users().messages().get(userId="me", id=message))

    if emails_details.count > 0:
      return emails_details
    else: 
      print("Not new emails")

  except HttpError as error:
    # TODO(developer) - Handle errors from gmail API.
    print(f"An error occurred: {error}")


if __name__ == "__main__":
  main()