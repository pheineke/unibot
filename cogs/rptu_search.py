import discord
from discord.ext import commands
import aiohttp
from bs4 import BeautifulSoup
import asyncio

DEPARTMENTS = [
    'INF', 'MAT', 'PHY', 'A', 'BI', 'BIO', 'CHE', 'EIT', 'EZW', 
    'KSW', 'MV', 'NUW', 'PSY', 'RU', 'SO', 'WIW', 'KSB', 'ZIDIS', 'ZKW', 'GS'
]

class RPTUSearch(commands.Cog):
    """Search the RPTU Module Handbook for courses and modules."""
    
    def __init__(self, bot):
        self.bot = bot
        self.all_modules = []
        self.is_loading = False
        self.bot.loop.create_task(self.load_all_modules())

    async def fetch_modules_for_department(self, session, dept):
        url = f"https://modhb.rptu.de/mhb/FB-{dept}/modules/"
        try:
            async with session.get(url, timeout=15) as response:
                if response.status != 200:
                    return []
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                modules = []
                
                rows = soup.select('table tbody tr')
                if not rows:
                    rows = soup.find_all('tr')
                    
                for row in rows:
                    tds = row.find_all('td')
                    if len(tds) >= 2:
                        mod_id = tds[0].get_text(strip=True)
                        name_link = tds[1].find('a')
                        name = tds[1].get_text(strip=True)
                        
                        semester = ''
                        language = ''
                        ects = 'Unknown'
                        location = ''
                        
                        if len(tds) >= 6:
                            semester = tds[2].get_text(strip=True)
                            language = tds[3].get_text(strip=True)
                            ects = tds[4].get_text(strip=True)
                            location = tds[5].get_text(strip=True)
                            
                        link = ''
                        if name_link and name_link.has_attr('href'):
                            link = 'https://modhb.rptu.de' + name_link['href']
                        elif mod_id and len(mod_id) > 5:
                            id_link = tds[0].find('a')
                            if id_link and id_link.has_attr('href'):
                                link = 'https://modhb.rptu.de' + id_link['href']
                                
                        if mod_id and name and link:
                            modules.append({
                                'id': mod_id,
                                'name': name,
                                'dept': dept,
                                'link': link,
                                'ects': ects,
                                'semester': semester,
                                'language': language,
                                'location': location
                            })
                return modules
        except Exception as e:
            print(f"Failed to fetch {dept}: {e}")
            return []

    async def load_all_modules(self):
        self.is_loading = True
        print(f"Loading RPTU modules database across {len(DEPARTMENTS)} departments...")
        all_modules = []
        async with aiohttp.ClientSession() as session:
            batch_size = 5
            for i in range(0, len(DEPARTMENTS), batch_size):
                batch = DEPARTMENTS[i:i + batch_size]
                tasks = [self.fetch_modules_for_department(session, dept) for dept in batch]
                results = await asyncio.gather(*tasks)
                for res in results:
                    all_modules.extend(res)
        self.all_modules = all_modules
        self.is_loading = False
        print(f"Total modules loaded: {len(self.all_modules)}")

    @commands.command(name="search")
    async def search(self, ctx, *args):
        """
        Searches for modules by ID, Name, Department, or other text.
        Usage: !search <search terms> [Dept Code] [-x]
        
        Options:
        - Department Codes: Filter by department (e.g. INF, MAT, A, BI)
        - Text: Any other text is used to filter modules (AND logic).
        - '-x': View up to 40 results (default is 10)
        
        Examples:
        !search Logik
        !search Grundlagen INF
        !search INF-02-05
        """
        if not args:
            await ctx.send("Please provide a search term (e.g., `!search Logik` or `!search INF-02-05`).")
            return

        args_list = list(args)
        show_more = False
        if '-x' in args_list:
            show_more = True
            args_list.remove('-x')
            
        display_query = " ".join(args_list)
        dept_filters = []
        text_filters = []
        
        for arg in args_list:
            upper = arg.upper()
            if upper in DEPARTMENTS:
                dept_filters.append(upper)
            else:
                text_filters.append(arg.lower())
                
        if self.is_loading or not self.all_modules:
            await ctx.send("Comparison database is still loading... please wait a moment.")
            return
            
        results = []
        for m in self.all_modules:
            if dept_filters and m['dept'] not in dept_filters:
                continue
                
            if not text_filters:
                if dept_filters:
                    results.append(m)
                continue
                
            module_text = f"{m['id']} {m['name']} {m['semester']} {m['language']} {m['location']} {m['dept']}".lower()
            
            if all(term in module_text for term in text_filters):
                results.append(m)
                
        if not results:
            await ctx.send(f"No modules found matching \"**{display_query}**\".")
            return
            
        limit = 40 if show_more else 10
        top_results = results[:limit]
        
        chunks = []
        current_chunk = f"Found **{len(results)}** matches for \"**{display_query}**\":\n"
        
        for m in top_results:
            credits = m['ects'].replace('LP', 'ECTS') if m.get('ects') else '? ECTS'
            sem = m.get('semester') or '?'
            lang = m.get('language') or '?'
            loc = m.get('location') or '?'
            
            entry = f"• **{m['id']}** {m['name']} [{credits}] [{sem}] [{lang}] [{loc}] - [Link]({m['link']})\n"
            
            if len(current_chunk) + len(entry) > 1950:
                chunks.append(current_chunk)
                current_chunk = entry
            else:
                current_chunk += entry
                
        if len(results) > limit:
            footer_msg = "Use `!search " + display_query + " -x` to see more." if not show_more else "Try a more specific search."
            footer = f"...and {len(results) - limit} more. {footer_msg}\n"
            if len(current_chunk) + len(footer) > 1950:
                chunks.append(current_chunk)
                current_chunk = footer
            else:
                current_chunk += footer
                
        chunks.append(current_chunk)
        
        for chunk in chunks:
            if chunk.strip():
                await ctx.send(chunk)

async def setup(bot):
    await bot.add_cog(RPTUSearch(bot))
