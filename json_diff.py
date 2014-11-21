#!/usr/bin/env python
import argparse
import json
import os
import re
import copy


class JSON_Diff:
    def __init__(self, json_file, json_model, list_depth=0):
        try:
            self.json_file = json.load(open(json_file))
        except IOError:
            print "JSON File not found. Check name and try again."
            self.json_file = None
            exit(1)

        model_json = []
        model_name = []
        self.is_directory = True
        if os.path.isfile(json_model):
            try:
                model_json.append(json.load(open(json_model)))
                model_name.append(json_model)
                self.is_directory = False
            except IOError:
                print "Model file not found. Check name and try again"
                exit(1)
        elif os.path.isdir(json_model):
            for item in os.listdir(json_model):
                try:
                    # make a tuple to store filename
                    if not json_model.endswith('/'):
                        json_model += '/'
                    filename = json_model + item
                    model_json.append(json.load(open(filename)))
                    model_name.append(item)
                except IOError:
                    print "Could not open file"
        else:
            print "File or directory not found. Check name and try again."
            exit(1)

        self.model = zip(model_json, model_name)
        self.difference = []
        # variable to control how deep to recursively search-- currently not used
        self.list_depth = list_depth

        # if len(self.model) < 1:
        # print "No files could be read in specified directory"


    def __clear_match_row__(self, match_table, row, cur_index):
        for i in range(len(match_table[0])):
            match_table[row][i] = 0
        match_table[row][cur_index] = 1

    def __clear_match_col__(self, match_table, col, cur_index):
        for i in range(len(match_table[0])):
            match_table[i][col] = 0
        match_table[cur_index][col] = 1

    def __one_to_one__(self, strings, regexes):
        dim = len(strings)  # =len(regexes)
        match_chart = [[0 for i in range(dim)] for j in range(dim)]

        # set up matching table
        # will be a 2d array with 0s indicating no match, and 1s indicating a match
        for r in range(dim):
            for s in range(dim):
                match = re.match(regexes[r], strings[s])
                if match:
                    match_chart[r][s] = 1

        # minimize match table
        # sum the rows and columns
        # rows
        sums = [sum(match_chart[k][:]) for k in range(dim)]
        # add in columns
        sums.extend(sum([match_chart[i][j] for i in range(dim)]) for j in range(dim))

        num_matches, index, turns_wo_match = 0, 0, 0
        max_index = 2 * dim
        minimized = [False for i in range(2 * dim)]
        # loop until all matched or no more minimizations possible
        while num_matches < max_index and turns_wo_match < max_index and not sums == [1] * (2 * dim):
            if sums[index] == 0:
                return {}  # no match for one of the fields
            elif sums[index] == 1 and not minimized[index]:
                # find coordinate
                #could write with more code reuse, but this is more intuitive to read
                if index < dim:  #in a row
                    for i in range(dim):
                        if match_chart[index][i] == 1:
                            self.__clear_match_col__(match_chart, i, index)
                            minimized[index] = True
                            continue
                else:  #in a col
                    for i in range(dim):
                        if match_chart[i][index] == 1:
                            self.__clear_match_row__(match_chart, i, index)
                            minimized[index] = True
                            continue
                turns_wo_match = 0
                num_matches += 1
                #update sums
                sums = [sum(match_chart[k][:]) for k in range(dim)]
                #add in columns
                sums.extend(sum([match_chart[i][j] for i in range(dim)]) for j in range(dim))

            else:
                turns_wo_match += 1

            index = (index + 1) % max_index

        if num_matches == max_index or sums == [1] * (2 * dim):
            final_mapping = {}
            for i in range(dim):
                # find match
                for j in range(dim):
                    if match_chart[i][j] == 1:
                        final_mapping[regexes[i]] = strings[j]
                        continue
            return final_mapping

        else:  # ambiguous
            print ("ERROR: ambiguous matching please fix your model to use more specific regexes")
            exit(1)

    def lists_equal(self, json_list, regex_list):
        # length check
        if not len(json_list) == len(regex_list):
            return False

        # go through indices and ensure they are all equal
        for index in range(len(json_list)):
            if not type(json_list[index]) == type(regex_list[index]):
                return False

            if type(json_list[index]) is dict:
                # do json comparison
                if not self.equals_model(json_list[index], regex_list[index]):
                    return False

            elif type(json_list[index]) is list:
                # another list comparison
                if not self.lists_equal(json_list[index], regex_list[index]):
                    return False

            elif type(json_list[index]) is unicode:
                # regex match
                if not re.match(regex_list[index], json_list[index]):
                    return False

            else:
                # some other type
                if not json_list[index] == regex_list[index]:
                    return False

        return True

    '''
    ' Our general process will be to read both inputs as json objects
    ' We will then conduct a DFS
    ' At each level, check that the size of the key set is the same
    ' Check that the key set has a 1-1 correspondence
    ' Check for each key that the values are the same
    '
    ' The model will treat all keys as regexes. All values will be dicts, lists, or regexes
    '''

    def equals_model(self, json_input, model):
        json_keys = []
        model_keys = []
        if type(json_input) is dict and type(model) is dict:
            json_keys = json_input.keys()
            model_keys = model.keys()
        elif type(json_input) is list and type(model) is list:
            return self.lists_equal(json_input, model)
        elif type(json_input) is not type(model):
            return False
        else:
            raise Exception("ERROR: Not proper JSON format")

        # check size
        if not len(json_keys) == len(model_keys):
            return False

        # check 1-1 correspondence
        key_matches = self.__one_to_one__(json_keys, model_keys)

        if not len(json_keys) == len(key_matches.keys()):
            return False

        # check values
        for key in key_matches.keys():
            if not type(json_input.get((key_matches[key]))) == type(model[key]):
                return False
            if type(model[key]) is dict:
                # recursive search
                if not self.equals_model(json_input.get(key_matches[key]), model[key]):
                    return False
                    # otherwise continue

            elif type(model[key]) is list:
                # lists are deterministic! yay!
                if not self.lists_equal(json_input.get(key_matches[key]), model[key]):
                    return False

            elif type(model[key]) is unicode:
                if not re.match(model[key], json_input.get(key_matches[key])):
                    return False

            # maybe an int or something?
            else:
                if not json_input.get(key_matches[key]) == model[key]:
                    return False

        # if we make it through all of this, hooray! Match
        return True


    '''
    ' This module assumes that we are passing to json files.
    ' To determine equivalence we will simply load both, and compare with
    ' direct equivalence
    '''

    def equalsJSON(self, _json1, _json2):
        return _json1 == _json2

    def diffModel(self, _json1, _json2, path='', depth=-1):
        if not type(_json1) == type(_json2):
            if type(_json2) is unicode and type(_json1) not in [list, dict]:
                # Potential regex match
                self.diffJSON_item(_json1, _json2, path, True)
            else:
                self.difference.append('TypeDifference : %s - %s: (%s), %s: (%s)' % (
                    path, type(_json1).__name__, str(_json1), type(_json2).__name__, str(_json2)))
        else:
            # they are the same type
            # Three choices: dict, list, item
            if type(_json1) is dict:
                self.diffJSON_dict(_json1, _json2, path, depth, True)
            elif type(_json1) is list:
                self.diffJSON_list(_json1, _json2, path, depth, True)
            else:
                self.diffJSON_item(_json1, _json2, path, True)

    '''
    ' This code computes the diff between two different JSON objects.
    ' It also computes a line by line delta to be used to determine similarity
    ' This scoring will be especially useful in the regex version as it will allow for easier classification
    '
    ' This code follows a very similar structure to https://github.com/monsur/jsoncompare/blob/master/jsoncompare.
    '
    ' Assume json1 is new and json2 is old
    '
    ' Depth should be -1 for full recursive search
    ' Depth == 0 -> do straight list or dict equivalence
    ' Depth > 0 do recursive search, but decrement depth so we do not search forever
    '''

    def diffJSON(self, _json1, _json2, path='', depth=-1):
        if not type(_json1) == type(_json2):
            self.difference.append('TypeDifference : %s - is %s: (%s), but was %s: (%s)' % (
                path, type(_json1).__name__, str(_json1), type(_json2).__name__, str(_json2)))
        else:
            # they are the same type
            # Three choices: dict, list, item
            if type(_json1) is dict:
                self.diffJSON_dict(_json1, _json2, path, depth, False)
            elif type(_json1) is list:
                self.diffJSON_list(_json1, _json2, path, depth, False)
            else:
                self.diffJSON_item(_json1, _json2, path, False)

    def diffJSON_dict(self, _json1, _json2, path, depth, useRegex):
        # Depth greater > 0 indicates we should compare keys
        # Negative depth means continuously recursively search
        if not depth == 0:
            json1_keys = _json1.keys()
            json2_keys = _json2.keys()
            matched_keys = []
            for key in json1_keys:
                if len(path) == 0:
                    new_path = key
                else:
                    new_path = '%s.%s' % (path, key)
                if key in json2_keys:
                    # match
                    matched_keys.append(key)
                    json2_keys.remove(key)
                else:
                    # key in json1 that is not in json2
                    #expand that k-v pair into diff
                    self.expandDiff(_json1[key], new_path, True)
            for key in json2_keys:
                if len(path) == 0:
                    new_path = key
                else:
                    new_path = '%s.%s' % (path, key)
                # all keys remaining are in 2, but not 1
                #expand these k-v pairs into diff as well
                self.expandDiff(_json2[key], new_path, False)

            # now that we have matched keys, recursively search
            for key in matched_keys:
                if len(path) == 0:
                    new_path = key
                else:
                    new_path = '%s.%s' % (path, key)
                #Decrement depth. If negative-> infinite otherwise get closer to 0
                if useRegex:
                    self.diffModel(_json1[key], _json2[key], new_path, depth - 1)
                else:
                    self.diffJSON(_json1[key], _json2[key], new_path, depth - 1)

    def diffJSON_list(self, _json1, _json2, path, depth, useRegex):
        # save a snapshot of difference for comparison in the different recursive branches
        current_difference = copy.deepcopy(self.difference)
        json1_matches = []
        json2_original = copy.deepcopy(_json2)
        # Try to find a match for each item in JSON1
        '''
        ' This WILL find a match for the first item in a a list of similar dictionaries
        ' even if later dictionaries in the list are a better match
        '
        ' TODO Fix this bug -- 2 pass diff?
        '''
        cur_index = 0
        for (index, item) in enumerate(_json1):
            prev_index = cur_index
            # map from the index in the list to irrelevance score
            #irrelevance score is higher the more unrelated-- 0 is perfect match
            index_to_irrelevance = {}
            #map from the index in the list to the changeset associated between this 'item' and _json2[index]
            index_to_changeset = {}
            while cur_index < len(_json2):
                if not useRegex and item == _json2[cur_index]:
                    #perfect match
                    index_to_irrelevance[cur_index] = 0
                    json1_matches.append(item)
                    _json2.remove(_json2[cur_index])
                    break
                elif useRegex and type(item) not in [list, dict]:
                    if (type(_json2[cur_index]) is unicode):
                        #we can use as a pattern though item could be an integer say
                        match = re.match(_json2[cur_index], str(item))
                        if match:
                            index_to_irrelevance[cur_index] = 0
                            json1_matches.append(item)
                            _json2.remove(_json2[cur_index])
                            break
                        else:
                            #no possible match
                            #todo should we include changeset?
                            index_to_irrelevance[cur_index] = -1
                    else:
                        #Can't use regex-- test strict equality
                        if (item == _json2[cur_index]):
                            #perfect match
                            index_to_irrelevance = 0
                            json1_matches.append(item)
                            _json2.remove(_json2[cur_index])
                        else:
                            #no match possible
                            index_to_irrelevance[cur_index] = -1
                            continue
                elif depth == 0 or type(item) not in [list, dict] or type(item) is not type(_json2[cur_index]):
                    #failed surface match
                    #might be a match later on in the list
                    index_to_irrelevance[cur_index] = -1  # to indicate no possible match
                else:
                    #failed, but do recursive search to find best match
                    new_path = "%s[%s]" % (path, index)
                    if useRegex:
                        self.diffModel(item, _json2[cur_index], new_path, depth - 1)
                    else:
                        self.diffJSON(item, _json2[cur_index], new_path, depth - 1)
                    #determine the difference of the recursive branch to find best match
                    index_to_irrelevance[cur_index] = len(
                        [diff_item for diff_item in self.difference if diff_item not in current_difference])
                    index_to_changeset[cur_index] = [diff_item for diff_item in self.difference if
                                                     diff_item not in current_difference]
                    #set difference back to before the diff
                    self.difference = copy.deepcopy(current_difference)
                cur_index += 1

            '''
            ' Matching strategy
            '
            ' 1) If there is a 0 irrelevance: perfect match, move to next item
            ' 2) If there are all -1 irrelevance: no match, pick lowest index
            ' 3) If there are any with > 0 irrelevance pick the lowest one as best match
            '     - In case of tie, lowest index wins
            '
            ' Known issue with deleting an item out of the first list
            ' We might need to fix this to make it a 2-pass diff
            '''
            indices = index_to_irrelevance.keys()
            if len(indices) == 0:
                break
            indices.sort()
            best_match_score = -1
            match_index = indices[0]
            for i in indices:
                if index_to_irrelevance[i] == 0:
                    best_match_score = 0
                    break
                elif index_to_irrelevance[i] < 0:
                    continue
                else:
                    if best_match_score < 0 or index_to_irrelevance[i] < best_match_score:
                        best_match_score = index_to_irrelevance[i]
                        match_index = i
            if best_match_score > 0:
                #treat as 'better than nothing match so we'll take it'
                self.difference.extend(index_to_changeset[match_index])
                json1_matches.append(item)
                _json2.remove(_json2[match_index])
                cur_index = match_index   # Should be the spot right after the match
            elif best_match_score < 0:
                cur_index = prev_index

        # At this point we have two lists with the items that could not be matched
        match_index = 0
        for index in range(len(_json1)):
            if match_index < len(json1_matches) and _json1[index] == json1_matches[match_index]:
                match_index += 1
            else:
                new_path = "%s[%s]" % (path, index)
                self.expandDiff(_json1[index], new_path, True)

        original_index = 0
        for index in range(len(_json2)):
            while not _json2[index] == json2_original[::-1][original_index]:
                original_index += 1
            new_path = "%s[%s]" % (path, len(json2_original) - original_index - 1)
            self.expandDiff(_json2[index], new_path, False)
            original_index += 1

    def diffJSON_item(self, _json1, _json2, path, useRegex):
        if useRegex and type(_json2) is unicode:
            match = re.match(_json2, str(_json1))
            if not match:
                self.difference.append('Changed: %s to %s from %s' % (path, _json1, _json2))
        else:
            if not _json1 == _json2:
                self.difference.append('Changed: %s to %s from %s' % (path, _json1, _json2))

    '''
    'Once we have found a mismatch in types, recursively add everything
    'at that level to the diff
    '
    'path is the current path of the item
    'new_item is true if we are in the new json (things added)
    'new_item is false if we are in in the old json (things removed)
    '''

    def expandDiff(self, blob, path, new_item):
        # Three possibilities: dict, list, item
        if new_item:
            c = '+'
        else:
            c = '-'
        if type(blob) is dict:
            for key in blob.keys():
                if len(path) == 0:
                    new_path = key
                else:
                    new_path = "%s.%s" % (path, key)
                if type(blob[key]) not in [list, dict]:
                    self.difference.append('%s: %s=%s' % (c, new_path, blob[key]))
                else:
                    self.expandDiff(blob[key], new_path, new_item)
        elif type(blob) is list:
            for (index, item) in enumerate(blob):
                new_path = "%s[%s]" % (path, index)
                if type(blob[index]) in (list, dict):
                    self.expandDiff(item[index], new_path, new_item)
                else:
                    self.difference.append('%s: %s=%s' % (c, new_path, blob[index]))
        else:
            self.difference.append('%s: %s=%s' % (c, path, blob))

    def comparison(self, useModel):
        for model in self.model:
            if useModel:
                if self.equals_model(self.json_file, model[0]):
                    return model[1] if self.is_directory else True
            else:
                if self.equalsJSON(self.json_file, model[0]):
                    return model[1] if self.is_directory else True
        # no match
        return False

    def diff(self, useModel):
        if useModel:
            self.diffModel(self.json_file, self.model[0][0])
        else:
            self.diffJSON(self.json_file, self.model[0][0])
        for change in self.difference:
            print change.encode('ascii', 'replace')
        difference = self.difference
        # Reinitialize so that we can run against multiple models
        self.difference = []
        self.list_depth = 0
        return difference


def main():
    p = argparse.ArgumentParser(
        description='Tool to check equivalence and difference of two JSON files with regex support',
        formatter_class=argparse.RawTextHelpFormatter,
        epilog='NOTE: If there are no regexes in your JSON use the j2j option\n\n'
               'Usage examples: \n\n'
               'To do JSON to JSON comparison (default behavior):\n'
               '   ./json_diff.py path/to/file1.json path/to/file2.json \n\n'

               'To compare a single json file against a directory of models:\n'
               '    ./json_diff.py -mode j2m path/to/file.json path/to/models \n\n'
               ''
               'To compute the diff between to JSON documents: \n'
               '    ./json_diff.py -d path/to/new.json path/to/old.json'

    )
    p.add_argument('--mode', choices=['j2j', 'j2m'], default='j2j',
                   help="Determine what mode to use. Default is %(default)s. j2m (json to model) for regex support")
    p.add_argument('-d', '--diff', action="store_true",
                   help="Set tool to do diff instead of comparison. (comparison if not flagged).")
    p.add_argument('json', help='The path of the json file')
    p.add_argument('json_model', metavar='json/json_model',
                   help="The path of the .json file or directory of .json models with regex support"
                        "**Note we currently do not support diffs between a file and a directory")

    options = p.parse_args()

    diff_engine = JSON_Diff(options.json, options.json_model)

    if options.diff:
        if os.path.isdir(options.json_model):
            raise Exception("Unsupported operation: We do not allow diff against a directory. Must provide a filename")
        else:
            diff_engine.diff(options.mode == 'j2m')
    else:
        print diff_engine.comparison(options.mode == 'j2m')


if __name__ == "__main__":
    main()