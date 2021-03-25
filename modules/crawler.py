import datetime
import time
import requests

from bs4 import BeautifulSoup
from recipe_scrapers import scrape_me

from modules.mongoHelper import MongoHelper

class Crawler(object):
    _recipeBuffer = 50
    _sleepTime = 1
    # _url is the visited links for the bfs
    _urls = set()
    _queue = []

    def __init__(self, website):
        self.website = website

    def begin(self):
        self.crawl()
        self.scrape()

    # this method use bfs to crawl all the websites into _urls field
    def crawl(self):
        self._urls.add(self.website.baseUrl)
        self._queue.append(self.website.baseUrl)
        while self._queue:
            try:
                href = self._queue.pop(0)
                print('Popped from queue: ', href)
                html_page = requests.get(href)
                soup = BeautifulSoup(html_page.text, 'html.parser')
                all_links = soup.find_all('a')
                for link in all_links:
                    hrefNeighbor = link.get('href')
                    if hrefNeighbor and hrefNeighbor.find(self.website.baseUrl) == 0 and hrefNeighbor not in self._urls:
                        self._urls.add(hrefNeighbor)
                        self._queue.append(hrefNeighbor)
            except Exception as e:
                print('Exception encountered while crawling: ', e)
                continue
        
    def scrape(self):
        recipes = []
        for url in self._urls:
            try:
                if MongoHelper.getRecipeByUrl(url).count() > 0:
                    print('Recipe is already in DB for URL:{}'.format(url))
                    continue
        
                scraper = scrape_me(url)
                if not self._isRecipe(scraper):
                    continue
                
                name = scraper.title()

                ingredients = scraper.ingredients()

                directions = scraper.instructions()

                servingCount = scraper.yields()
                
                totalTime = scraper.total_time()
                
                image = scraper.image()

                ratings = scraper.ratings()
                
                recipe = {'name': name, 'url': url, 'ingredients': ingredients, 'directions': directions, 
                'servingCount': servingCount, 'image': image, 'totalTime': totalTime, 'sourceName': self.website.name, 
                'ratings': ratings, 'scrapeTime': datetime.datetime.now(), 'language': self.website.language}

                recipes.append(recipe)
                print('Scraped Recipe: {}, from URL: {}, RecipeBatch#: {}'.format(name, url, len(recipes)))
                
                if len(recipes) >= self._recipeBuffer:
                    recipeIds = MongoHelper.insertRecipes(recipes)
                    recipes = []
                    print('{} Recipes have been successfully written: {}'.format(Crawler._recipeBuffer, recipeIds))

                time.sleep(self._sleepTime) # Sleeping between requests to avoid limit
            except:
                print('Could not parse url: ', url)
                continue

    def _isRecipe(self, scraper):
        name = scraper.title()
        if len(name) == 0 or name == '' or name is None:
            print('Could not find Name for URL: {}'.format(scraper.url))
            return False

        directions = scraper.instructions()
        if len(directions) == 0 or directions == '' or directions is None:
            print('Could not find Directions for URL: {}'.format(scraper.url))
            return False

        ingredients = scraper.ingredients()
        if len(ingredients) == 0 or ingredients == '' or ingredients is None:
            print('Could not find Ingredients for URL: {}'.format(scraper.url))
            return False
        
        return True
