#!/usr/bin/env python
# encoding: UTF-8

"""
This file is part of commix project (http://commixproject.com).
Copyright (c) 2014-2017 Anastasios Stasinopoulos (@ancst).

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
 
For more see the file 'readme/COPYING' for copying permission.
"""

import re
import sys
import base64
import urllib2
import urlparse
import httplib

from src.utils import logs
from src.utils import menu
from src.utils import settings

from src.core.injections.controller import checks
from src.thirdparty.colorama import Fore, Back, Style, init

"""
Checking the HTTP response content.
"""
def http_response_content(content):
  info_msg = "The target's HTTP response page content:"
  if settings.VERBOSITY_LEVEL >= 4:
    print settings.print_info_msg(info_msg)
  if menu.options.traffic_file: 
    logs.log_traffic("-" * 42 + "\n" + info_msg + "\n" + "-" * 42)  
  if settings.VERBOSITY_LEVEL >= 4:
    print settings.print_http_response_content(content)
  if menu.options.traffic_file:
    logs.log_traffic("\n" + content)
  if menu.options.traffic_file:
    logs.log_traffic("\n\n" + "#" * 77 + "\n\n")

"""
Checking the HTTP response headers.
"""
def http_response(headers):
  info_msg = "The target's HTTP response headers:"
  if settings.VERBOSITY_LEVEL >= 3:
    print settings.print_info_msg(info_msg)
  if menu.options.traffic_file: 
    logs.log_traffic("-" * 37 + "\n" + info_msg + "\n" + "-" * 37)  
  response_http_headers = str(headers).split("\r\n")
  for header in response_http_headers:
    if len(header) > 1: 
      if settings.VERBOSITY_LEVEL >= 3:
        print settings.print_traffic(header)
      if menu.options.traffic_file:
        logs.log_traffic("\n" + header)
  if menu.options.traffic_file:
    if settings.VERBOSITY_LEVEL <= 3: 
      logs.log_traffic("\n\n" + "#" * 77 + "\n\n")
    else:
      logs.log_traffic("\n\n")    

"""
Checking the HTTP Headers.
"""
def check_http_traffic(request):

  class do_connection(httplib.HTTPConnection, httplib.HTTPSConnection):
    """
    Checking the HTTP / HTTPS requests.
    """
    def request(self, method, url, body, headers):
      info_msg = "The provided HTTP request headers: "
      if settings.VERBOSITY_LEVEL >= 2:
        print settings.print_info_msg(info_msg)
      if menu.options.traffic_file: 
        logs.log_traffic("-" * 37 + "\n" + info_msg + "\n" + "-" * 37)
      header = method + " " + url
      if settings.VERBOSITY_LEVEL >= 2:
        print settings.print_traffic(header)
      if menu.options.traffic_file:
        logs.log_traffic("\n" + header)
      for item in headers.items():
        header = item[0] + ": " + item[1]
        if settings.VERBOSITY_LEVEL >= 2:
          print settings.print_traffic(header)
        if menu.options.traffic_file:
          logs.log_traffic("\n" + header)
      if body :
        header = body
        if settings.VERBOSITY_LEVEL >= 2:
          print settings.print_traffic(header)
        if menu.options.traffic_file:
          logs.log_traffic("\n" + header) 
      if menu.options.traffic_file:
        logs.log_traffic("\n\n")

      if settings.PROXY_PROTOCOL == 'https':
        httplib.HTTPSConnection.request(self, method, url, body, headers)
      else:
        httplib.HTTPConnection.request(self, method, url, body, headers)

  class connection_handler(urllib2.HTTPHandler, urllib2.HTTPSHandler):
    if settings.PROXY_PROTOCOL == 'https':
      def https_open(self, req):
        return self.do_open(do_connection, req)
    else:      
      def http_open(self, req):
        return self.do_open(do_connection, req)      

  opener = urllib2.OpenerDirector()
  opener.add_handler(connection_handler())
  response = opener.open(request)
  # Check the HTTP response headers.
  http_response(response.info())
  # Check the HTTP response content.
  http_response_content(response.read())

"""
Check for added headers.
"""
def do_check(request):

  # Check if defined any HTTP Host header.
  if menu.options.host:
    request.add_header('Host', menu.options.host)

  # Check if defined any HTTP User-Agent header.
  if menu.options.agent:
    request.add_header('User-Agent', menu.options.agent)

  # Check if defined any HTTP Referer header.
  if menu.options.referer and settings.REFERER_INJECTION == False:
    request.add_header('Referer', menu.options.referer)
        
  # Check if defined any HTTP Cookie header.
  if menu.options.cookie and settings.COOKIE_INJECTION == False:
    request.add_header('Cookie', menu.options.cookie)

  # Check if defined any HTTP Authentication credentials.
  # HTTP Authentication: Basic / Digest Access Authentication.
  if not menu.options.ignore_401:
    if menu.options.auth_cred and menu.options.auth_type:
      try:
        settings.SUPPORTED_HTTP_AUTH_TYPES.index(menu.options.auth_type)
        if menu.options.auth_type == "basic":
          b64_string = base64.encodestring(menu.options.auth_cred).replace('\n', '')
          request.add_header("Authorization", "Basic " + b64_string + "")
        elif menu.options.auth_type == "digest":
          try:
            url = menu.options.url
            try:
              response = urllib2.urlopen(url)
            except urllib2.HTTPError, e:
              try:
                authline = e.headers.get('www-authenticate', '')  
                authobj = re.match('''(\w*)\s+realm=(.*),''',authline).groups()
                realm = authobj[1].split(',')[0].replace("\"","")
                user_pass_pair = menu.options.auth_cred.split(":")
                username = user_pass_pair[0]
                password = user_pass_pair[1]
                authhandler = urllib2.HTTPDigestAuthHandler()
                authhandler.add_password(realm, url, username, password)
                opener = urllib2.build_opener(authhandler)
                urllib2.install_opener(opener)
                result = urllib2.urlopen(url)
              except AttributeError:
                pass
          except urllib2.HTTPError, e:
            pass
      except ValueError:
        err_msg = "Unsupported / Invalid HTTP authentication type '" + menu.options.auth_type + "'."
        err_msg += " Try basic or digest HTTP authentication type."
        print settings.print_critical_msg(err_msg)
        sys.exit(0)   
    else:
      pass        
    
  # The MIME media type for JSON.
  if settings.IS_JSON:
    request.add_header("Content-Type", "application/json")

  # Check if defined any extra HTTP headers.
  if menu.options.headers:
    # Do replacement with the 'INJECT_HERE' tag, if the wildcard char is provided.
    menu.options.headers = checks.wildcard_character(menu.options.headers)
    extra_headers = menu.options.headers
    extra_headers = extra_headers.split(":")
    extra_headers = ':'.join(extra_headers)
    extra_headers = extra_headers.split("\\n")
    # Remove empty strings
    extra_headers = [x for x in extra_headers if x]
    for extra_header in extra_headers:
      # Extra HTTP Header name 
      http_header_name = re.findall(r"(.*):", extra_header)
      http_header_name = ''.join(http_header_name)
      # Extra HTTP Header value
      http_header_value = re.findall(r":(.*)", extra_header)
      http_header_value = ''.join(http_header_value)
      # Check if it is a custom header injection.
      if settings.CUSTOM_HEADER_INJECTION == False and \
         settings.INJECT_TAG in http_header_value:
        settings.CUSTOM_HEADER_INJECTION = True
        settings.CUSTOM_HEADER_NAME = http_header_name
      request.add_header(http_header_name, http_header_value)

#eof
