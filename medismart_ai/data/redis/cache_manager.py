
# data/redis/cache_manager.py
import redis
import json
import pickle
from utils.logger import get_logger
import time

logger = get_logger(__name__)

class CacheManager:
    """Redis cache manager for the medical system"""
    
    def __init__(self, host='localhost', port=6379, db=0, password=None, expire_time=3600):
        """
        Initialize Redis cache manager
        
        Args:
            host: Redis host
            port: Redis port
            db: Redis DB number
            password: Redis password
            expire_time: Default cache expiration time in seconds
        """
        try:
            self.redis_client = redis.Redis(
                host=host,
                port=port,
                db=db,
                password=password,
                decode_responses=False
            )
            self.expire_time = expire_time
            logger.info(f"Connected to Redis: {host}:{port}")
            
        except redis.ConnectionError as e:
            logger.error(f"Failed to connect to Redis: {str(e)}")
            raise
            
    def _generate_key(self, key_type, key_id):
        """
        Generate a standardized Redis key
        
        Args:
            key_type: Type of the key (e.g., 'prescription', 'patient')
            key_id: ID or unique identifier
            
        Returns:
            str: Formatted Redis key
        """
        return f"{key_type}:{key_id}"
        
    def set(self, key_type, key_id, data, expire_time=None):
        """
        Set data in cache
        
        Args:
            key_type: Type of the key
            key_id: ID or unique identifier
            data: Data to cache (will be pickled)
            expire_time: Custom expiration time in seconds
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            key = self._generate_key(key_type, key_id)
            if expire_time is None:
                expire_time = self.expire_time
                
            # Pickle the data to preserve type information
            pickled_data = pickle.dumps(data)
            
            # Set the value with expiration
            success = self.redis_client.setex(key, expire_time, pickled_data)
            
            if success:
                logger.debug(f"Cached {key_type}:{key_id}")
            else:
                logger.warning(f"Failed to cache {key_type}:{key_id}")
                
            return success
            
        except Exception as e:
            logger.error(f"Error caching {key_type}:{key_id}: {str(e)}")
            return False
            
    def get(self, key_type, key_id):
        """
        Get data from cache
        
        Args:
            key_type: Type of the key
            key_id: ID or unique identifier
            
        Returns:
            object: Cached data or None if not found
        """
        try:
            key = self._generate_key(key_type, key_id)
            data = self.redis_client.get(key)
            
            if data:
                # Unpickle the data
                unpickled_data = pickle.loads(data)
                logger.debug(f"Cache hit for {key_type}:{key_id}")
                return unpickled_data
            else:
                logger.debug(f"Cache miss for {key_type}:{key_id}")
                return None
                
        except Exception as e:
            logger.error(f"Error retrieving from cache {key_type}:{key_id}: {str(e)}")
            return None
            
    def delete(self, key_type, key_id):
        """
        Delete data from cache
        
        Args:
            key_type: Type of the key
            key_id: ID or unique identifier
            
        Returns:
            bool: True if deleted, False otherwise
        """
        try:
            key = self._generate_key(key_type, key_id)
            result = self.redis_client.delete(key)
            
            success = result > 0
            if success:
                logger.debug(f"Deleted from cache {key_type}:{key_id}")
            else:
                logger.debug(f"Key not found in cache {key_type}:{key_id}")
                
            return success
            
        except Exception as e:
            logger.error(f"Error deleting from cache {key_type}:{key_id}: {str(e)}")
            return False
            
    def flush_by_pattern(self, pattern):
        """
        Delete keys matching a pattern
        
        Args:
            pattern: Redis key pattern (e.g., 'prescription:*')
            
        Returns:
            int: Number of keys deleted
        """
        try:
            cursor = 0
            deleted_count = 0
            
            while True:
                cursor, keys = self.redis_client.scan(cursor, pattern, 100)
                if keys:
                    deleted_count += self.redis_client.delete(*keys)
                
                if cursor == 0:
                    break
                    
            logger.info(f"Flushed {deleted_count} keys matching pattern '{pattern}'")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Error flushing keys with pattern '{pattern}': {str(e)}")
            return 0
            
    def set_json(self, key_type, key_id, json_data, expire_time=None):
        """
        Set JSON data in cache
        
        Args:
            key_type: Type of the key
            key_id: ID or unique identifier
            json_data: JSON-serializable data
            expire_time: Custom expiration time in seconds
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Convert to JSON string
            json_string = json.dumps(json_data)
            
            # Store as regular string
            return self.set(key_type, key_id, json_string, expire_time)
            
        except Exception as e:
            logger.error(f"Error caching JSON for {key_type}:{key_id}: {str(e)}")
            return False
            
    def get_json(self, key_type, key_id):
        """
        Get JSON data from cache
        
        Args:
            key_type: Type of the key
            key_id: ID or unique identifier
            
        Returns:
            object: Deserialized JSON data or None if not found
        """
        try:
            # Get the JSON string
            json_string = self.get(key_type, key_id)
            
            if json_string:
                # Parse JSON
                return json.loads(json_string)
            else:
                return None
                
        except Exception as e:
            logger.error(f"Error retrieving JSON from cache {key_type}:{key_id}: {str(e)}")
            return None

    def cache_with_fallback(self, key_type, key_id, fallback_func, expire_time=None):
        """
        Get data from cache or execute fallback function if not found
        
        Args:
            key_type: Type of the key
            key_id: ID or unique identifier
            fallback_func: Function to execute if cache miss
            expire_time: Custom expiration time for the cache
            
        Returns:
            object: Data from cache or from fallback function
        """
        try:
            # Try to get from cache
            cached_data = self.get(key_type, key_id)
            
            if cached_data is not None:
                return cached_data
                
            # Cache miss, execute fallback function
            logger.debug(f"Cache miss for {key_type}:{key_id}, executing fallback")
            data = fallback_func()
            
            # Cache the result
            if data is not None:
                self.set(key_type, key_id, data, expire_time)
                
            return data
            
        except Exception as e:
            logger.error(f"Error in cache_with_fallback for {key_type}:{key_id}: {str(e)}")
            # Execute fallback on error
            return fallback_func()

    def health_check(self):
        """
        Check if Redis connection is healthy
        
        Returns:
            bool: True if healthy, False otherwise
        """
        try:
            return self.redis_client.ping()
        except Exception as e:
            logger.error(f"Redis health check failed: {str(e)}")
            return False
