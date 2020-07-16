#  Stuff we need to remove:
#  - Reposted message logs
#  - Command logs


#  Elastic indexes:
#  - logs_str - time
#  - guild_message_str - _id


import yaml
import asyncio
from elastic import ElasticSearchClient
from datetime import datetime, timedelta


DISCORD_EPOCH = 1420070400000


async def main(config):
    client = ElasticSearchClient(hosts=config["elastic_uri"])
    now = datetime.now()
    #  We keep data for up to 30 days, so we should delete it at 29 days
    delete_time = timedelta(days=29)

    async with client as db:
        logs_ids = []
        async for model in db._scroll(index="logs_str", body={"_source": "time"}):
            time_created = datetime.fromisoformat(model["_source"]["time"])
            if (now - time_created) > delete_time:
                logs_ids.append(model["_id"])
        await db.bulk_delete(index="logs_str", ids=logs_ids)
        del logs_ids

        message_ids = []
        async for model in db._scroll(index="guild_message_str", body={"_source": False}):
            id = model["_id"]
            time_created = datetime.utcfromtimestamp(((int(id) >> 22) + DISCORD_EPOCH) / 1000)
            if (now - time_created) > delete_time:
                message_ids.append(id)
        await db.bulk_delete(index="guild_message_str", ids=message_ids)
        del message_ids


if __name__ == "__main__":
    with open("config.yaml") as conf_file:
        config = yaml.load(conf_file, Loader=yaml.SafeLoader)

    asyncio.run(main(config))
