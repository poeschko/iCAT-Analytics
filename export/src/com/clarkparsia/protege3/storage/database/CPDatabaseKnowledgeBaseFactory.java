package com.clarkparsia.protege3.storage.database;

import edu.stanford.smi.protege.resource.Text;
import edu.stanford.smi.protege.storage.database.DatabaseFrameDb;
import edu.stanford.smi.protege.storage.database.DatabaseKnowledgeBaseFactory;

public class CPDatabaseKnowledgeBaseFactory extends
        DatabaseKnowledgeBaseFactory {
    
    @Override
    public Class<? extends DatabaseFrameDb> getDatabaseFrameDbClass() {
        return CPDatabaseFrameDb.class;
    }
    
    @Override
    public String getDescription() {
        return "Clark-Parsia " + Text.getProgramName() + " Database";
    }

}
