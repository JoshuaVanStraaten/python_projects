import requests
from datetime import datetime, timezone
import json
from pytz import timezone

NOTION_TOKEN = "<notion_token>"
DATABASE_ID = "<notion_db_id>"
GHUB_USERNAME = "<github_username>"
GHUB_TOKEN = "<github_token>"

headers = {
    "Authorization": "Bearer " + NOTION_TOKEN,
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28",
}

def get_pages(num_pages=None):
    """
    Get pages from the Notion database.

    Parameters:
    num_pages (int): The number of pages to retrieve. If None, retrieve all pages.

    Returns:
    list: A list of pages from the Notion database.

    """
    url = f"https://api.notion.com/v1/databases/{DATABASE_ID}/query"

    get_all = num_pages is None
    page_size = 100 if get_all else num_pages

    payload = {"page_size": page_size}
    response = requests.post(url, json=payload, headers=headers)

    data = response.json()

    # Comment this out to dump all data to a file
    with open('db.json', 'w', encoding='utf8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    
    results = data["results"]
    while data["has_more"] and get_all:
        payload = {"page_size": page_size, "start_cursor": data["next_cursor"]}
        url = f"https://api.notion.com/v1/databases/{DATABASE_ID}/query"
        response = requests.post(url, json=payload, headers=headers)
        data = response.json()
        results.extend(data["results"])

    return results

def create_page(data: dict):
    """
    Create page in the Notion database.

    Parameters:
    data (dict): Data to populate within the database.

    """
    create_url = "https://api.notion.com/v1/pages"

    payload = {"parent": {"database_id": DATABASE_ID}, "properties": data}

    res = requests.post(create_url, headers=headers, json=payload)
    print(res.status_code)
    return res


def update_page(page_id: str, data: dict):
    """
    Update page within the Notion database.

    Parameters:
    page_id (string): ID of the page to update.
    data (dict): Data to update within page.

    """
    url = f"https://api.notion.com/v1/pages/{page_id}"

    payload = {"properties": data}

    res = requests.patch(url, json=payload, headers=headers)
    print(res.status_code)
    return res

def delete_page(page_id: str):
    """
    Delete within the Notion database.

    Parameters:
    page_id (string): ID of the page to delete.

    """
    url = f"https://api.notion.com/v1/pages/{page_id}"

    payload = {"archived": True}

    res = requests.patch(url, json=payload, headers=headers)
    print(res.status_code)
    return res


def get_review_requests():
    url = f"https://api.github.com/search/issues?q=is:pr+review-requested:{GHUB_USERNAME}"
    headers = {'Authorization': f'token {GHUB_TOKEN}'}
    
    response = requests.get(url, headers=headers)
    print(response.status_code)

    pull_requests = response.json().get('items', [])
    pr_info = {}
    for pr in pull_requests:
        if pr['state'] == "open":
            # Parse the 'created_at' string into a datetime object
            created_at = datetime.strptime(pr['created_at'], "%Y-%m-%dT%H:%M:%SZ")
            # Format the datetime object into the desired string format
            formatted_created_at = created_at.strftime("%B %d, %Y %H:%M")

            pr_info[pr['title']] = {
                "url": pr['html_url'],
                "requestor": pr['user']['login'],
                "created": formatted_created_at
            }

    return pr_info

def populate_notion_db():
    # Get the pull request information
    pr_info = get_review_requests()
    updated_urls = {pr['url'] for pr in pr_info.values()}

    # Get current Notion DB information
    pages = get_pages()
    curr_pages = {}
    for page in pages:
        try:
            page_id = page["id"]
            url = page["properties"]["URL"]["title"][0]["text"]["content"]
            curr_pages[url] = page_id
        except IndexError:
            pass

    # Loop through the pull request information
    for title, info in pr_info.items():
        url = info["url"]
        if url not in curr_pages:
            # Prepare the data for the Notion page
            published_date = datetime.strptime(info["created"], "%B %d, %Y %H:%M")
            published_date = published_date.replace(tzinfo=timezone('UTC')).isoformat()
            data = {
                "Title": {"rich_text": [{"text": {"content": title}}]},
                "Published": {"date": {"start": published_date, "end": None}},
                "Requestor": {"rich_text": [{"text": {"content": info["requestor"]}}]},
                "URL": {"title": [{"text": {"content": url}}]}
            }
            # Create the Notion page
            create_page(data)

    # Delete pages that are not in the updated URLs
    for url, page_id in curr_pages.items():
        if url not in updated_urls:
            delete_page(page_id)


def main():
    populate_notion_db()


if __name__ == "__main__":
    main()
