# ==================== LIVERY INJECTION WRAPPER ====================
import asyncio
import json
import time
import requests
from concurrent.futures import ThreadPoolExecutor
from typing import Tuple, Dict, Any, Optional

class LiveryInjector:
    """Async wrapper for livery injection with thread executor"""
    
    # Copy the add_livery function from liveryInjectsv2.py
    @staticmethod
    def add_livery(item_id: str, auth_token: str, playfab_token: str) -> Tuple[bool, Dict]:
        """
        Inject livery to game account.
        This is a blocking operation that runs in thread executor.
        """
        base_url = "https://be38c.playfabapi.com/Client/ExecuteCloudScript"
        params = "?sdk=UnitySDK-2.212.250428&engine=6000.1.5f1&platform=Android"
        url = base_url + params
        
        headers = {
            'User-Agent': "UnityPlayer/6000.1.5f1 (UnityWebRequest/1.0, libcurl/8.10.1-DEV)",
            'Accept-Encoding': "deflate, gzip",
            'Content-Type': "application/json",
            'X-ReportErrorAsSuccess': "true",
            'X-PlayFabSDK': "UnitySDK-2.212.250428",
            'X-Authorization': auth_token,
            'X-Unity-Version': "6000.1.5f1"
        }
        
        try:
            start_time = time.time()
            
            # First request: Grant item
            payload_1 = {
                "CustomTags": None,
                "FunctionName": "ExecuteGrantItems",
                "FunctionParameter": {"itemIds": [item_id]},
                "GeneratePlayStreamEvent": False
            }
            
            response_1 = requests.post(url, data=json.dumps(payload_1), headers=headers, timeout=30)
            response_1.raise_for_status()
            response_1_data = response_1.json()
            
            function_result = response_1_data.get('data', {}).get('FunctionResult', {})
            item_instance_id, extracted_item_id = None, None
            
            if 'grantedItems' in function_result and function_result['grantedItems']:
                gi = function_result['grantedItems'][0]
                item_instance_id = gi.get('ItemInstanceId')
                extracted_item_id = gi.get('ItemId')
            elif 'ItemGrantResults' in function_result and function_result['ItemGrantResults']:
                igr = function_result['ItemGrantResults'][0]
                item_instance_id = igr.get('ItemInstanceId')
                extracted_item_id = igr.get('ItemId')
            elif 'itemInstanceId' in function_result:
                item_instance_id = function_result.get('itemInstanceId')
                extracted_item_id = function_result.get('itemId', item_id)
            
            if not item_instance_id:
                return False, {
                    "error": "Missing itemInstanceId in response",
                    "response": response_1_data
                }
            
            # Second request: Upload custom data
            payload_2 = {
                "CustomTags": None,
                "FunctionName": "UploadCustomDataWithItem",
                "FunctionParameter": {
                    "itemInstanceId": item_instance_id,
                    "itemId": extracted_item_id or item_id
                },
                "GeneratePlayStreamEvent": False
            }
            
            response_2 = requests.post(url, data=json.dumps(payload_2), headers=headers, timeout=30)
            response_2.raise_for_status()
            
            execution_time = int((time.time() - start_time) * 1000)
            
            return True, {
                "success": True,
                "itemInstanceId": item_instance_id,
                "itemId": extracted_item_id or item_id,
                "response1_status": response_1.status_code,
                "response2_status": response_2.status_code,
                "execution_time_ms": execution_time
            }
        
        except requests.exceptions.Timeout:
            return False, {"error": "Request timeout"}
        except requests.exceptions.ConnectionError:
            return False, {"error": "Connection error"}
        except requests.exceptions.RequestException as e:
            return False, {"error": f"Request error: {str(e)}"}
        except Exception as e:
            return False, {"error": str(e)}
    
    def __init__(self):
        self.executor = ThreadPoolExecutor(max_workers=5)
    
    async def inject_async(self, item_id: str, auth_token: str, playfab_token: str) -> Tuple[bool, Dict]:
        """
        Async wrapper for add_livery injection.
        Runs blocking operation in thread executor.
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self.executor,
            self.add_livery,
            item_id,
            auth_token,
            playfab_token
        )
    
    def shutdown(self):
        """Shutdown thread executor"""
        self.executor.shutdown(wait=True)
