from .random import Random
from .recommender import Recommender
import random
from collections import defaultdict
from random import randint


class ContextualImproved(Recommender):

    def __init__(self, tracks_redis, listened, first_songs, catalog):
        
        self.tracks_redis = tracks_redis
        self.fallback = Random(tracks_redis)
        self.catalog = catalog
        
        self.listened = listened
        self.first_songs = first_songs
        self.time_threshold = 0.6
        self.buffer_size = 20

    def recommend_next(self, user: int, prev_track: int, prev_track_time: float) -> int:

        listened = self.listened.get(user)
        first_track = self.first_songs.get(user)
        
        if first_track is None:
            first_track = prev_track
            self.first_songs.set(user, self.catalog.to_bytes(prev_track))
        else:   
            first_track = self.catalog.from_bytes(first_track)
            
        if listened is not None:
            listened = list(self.catalog.from_bytes(listened))
        else:
            listened = []
            self.listened.set(user, self.catalog.to_bytes([first_track]))
            
        track_data = self.tracks_redis.get(prev_track)
        
        if prev_track_time < self.time_threshold or track_data is None:
            prev_track = first_track
            track_data = self.tracks_redis.get(prev_track)
        else:
            listened.append(prev_track)
            if len(listened) > self.buffer_size:
                listened = listened[1:]
            self.listened.set(user, self.catalog.to_bytes(listened))


        cur_track_data = self.catalog.from_bytes(track_data)
        recommendations = cur_track_data.recommendations
        
        while recommendations is None:
            if listened != []:
                a = random.choice(listened)
                recommendations = a.recommendations
            else:
                return self.fallback.recommend_next(user, prev_track, prev_track_time)
            
        for tr in recommendations:
            if tr not in listened:
                listened.append(tr)
                if len(listened) > self.buffer_size:
                    listened = listened[1:]
                self.listened.set(user, self.catalog.to_bytes(listened))
                return tr
     
        return self.fallback.recommend_next(user, prev_track, prev_track_time)
