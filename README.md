
# YaTube
__YaTube__ is a social network for blogs. Here you can create posts, view
publications, comment, join groups and subscribe to other authors.

Stack: 
- Python==3.7
- Django~=2.2
- HTML5
- CSS (Bootstrap)

# Installation guide
1. Clone the repository:
```
git clone <url>
```
2. Create and activate virtual environment:
```
python -m venv <env_name>
source venv/Scripts/activate
```
3. Install all requirements:
```
pip install -r requirements.txt
```
4. Apply all migrations:
```
python manage.py migrate
```
5. Run the server:
```
python manage.py runserver
```